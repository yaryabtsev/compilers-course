from collections import defaultdict
from html import escape

from tasks.branch_conditions import SymbolicBranchDump


class HotVariableDump:
    def __init__(self, lexemes, edges, name, alpha=0.35, beta=0.5):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.alpha = alpha
        self.beta = beta
        self.branch_info = SymbolicBranchDump(lexemes, edges, name)
        self.branch_uses = self.collect_branch_uses()
        self.local_dependency_branch_uses = self.collect_local_dependency_branch_uses()
        self.cfg_dependency_branch_uses = self.collect_cfg_dependency_branch_uses()
        self.versioned_dependency_branch_uses = self.collect_versioned_dependency_branch_uses()
        self.versioned_source_dependency_branch_uses = self.normalize_versioned_uses(
            self.versioned_dependency_branch_uses
        )
        self.branch_successors = self.collect_branch_successors()
        self.variables = self.collect_variables(self.branch_uses)
        self.local_dependency_variables = self.collect_variables(self.local_dependency_branch_uses)
        self.cfg_dependency_variables = self.collect_variables(self.cfg_dependency_branch_uses)
        self.versioned_dependency_variables = self.collect_variables(self.versioned_dependency_branch_uses)
        self.versioned_source_dependency_variables = self.collect_variables(
            self.versioned_source_dependency_branch_uses
        )
        self.q_t_syntactic = self.build_q_t(self.branch_uses)
        self.q_t_local_dependency = self.build_q_t(self.local_dependency_branch_uses)
        self.q_t_cfg_dependency = self.build_q_t(self.cfg_dependency_branch_uses)
        self.q_t_versioned_dependency = self.build_q_t(self.versioned_dependency_branch_uses)
        # Backward-compatible default for code paths that expect a single Q_t value.
        self.q_t = self.q_t_syntactic
        self.q_add = self.build_q_add(self.branch_uses, self.variables)
        self.q_add_local_dependency = self.build_q_add(
            self.local_dependency_branch_uses, self.local_dependency_variables
        )
        self.q_add_cfg_dependency = self.build_q_add(
            self.cfg_dependency_branch_uses, self.cfg_dependency_variables
        )
        self.q_add_versioned_dependency = self.build_q_add(
            self.versioned_dependency_branch_uses, self.versioned_dependency_variables
        )
        self.q_add_versioned_source_dependency = self.build_q_add(
            self.versioned_source_dependency_branch_uses, self.versioned_source_dependency_variables
        )

    def table(self):
        return self.make_table(
            self.q_add,
            self.q_t_syntactic,
            f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; syntactic C relation',
            '<comment>Q<sub>t</sub> and Q<sub>add</sub> follow the QCE recurrence from Efficient State Merging, '
            'with C approximated by syntactic variable occurrence in branch conditions. '
            'The dump does not estimate SMT or ite expression cost.</comment>'
        )

    def tables(self, output_dir=None):
        sections = [
            ('Algorithm metrics', *self.metrics_table()),
            ('Syntactic branch variables', *self.table()),
            ('Local dependency variables', *self.make_table(
                self.q_add_local_dependency,
                self.q_t_local_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; local dependency C relation',
                '<comment>Local dependency mode expands branch variables through assignments inside the same block. '
                'It does not propagate dependencies across CFG edges.</comment>'
            )),
            ('CFG dependency variables', *self.make_table(
                self.q_add_cfg_dependency,
                self.q_t_cfg_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; cfg dependency C relation',
                '<comment>CFG dependency mode propagates assignment dependencies across CFG edges with set union at joins. '
                'It is still syntactic and does not check path feasibility.</comment>'
            )),
            ('Versioned dependency variables', *self.make_table(
                self.q_add_versioned_dependency,
                self.q_t_versioned_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; versioned dependency C relation',
                '<comment>Versioned dependency mode propagates source-definition versions across CFG edges. '
                'It is path-insensitive and does not check path feasibility.</comment>'
            )),
        ]
        if output_dir is not None:
            sections.append(self.algorithm_comparison_section(output_dir))
        return sections

    def metrics_table(self):
        rows = []
        reference = self.source_q_add(self.q_add_cfg_dependency)
        inputs = [
            ('Syntactic', self.branch_uses, self.q_add, self.q_t_syntactic),
            ('Local dependency', self.local_dependency_branch_uses,
             self.q_add_local_dependency, self.q_t_local_dependency),
            ('CFG dependency', self.cfg_dependency_branch_uses,
             self.q_add_cfg_dependency, self.q_t_cfg_dependency),
            ('Versioned dependency', self.versioned_dependency_branch_uses,
             self.q_add_versioned_dependency, self.q_t_versioned_dependency),
        ]
        for label, uses, q_add_source, q_t_source in inputs:
            source_q_add = self.source_q_add(q_add_source)
            rows.append([
                label,
                str(len(self.collect_variables(uses))),
                str(sum(1 for block_uses in uses if block_uses)),
                self.format_number(max(q_t_source) if q_t_source else 0.0),
                self.format_number(sum(sum(values) for values in q_add_source.values())),
                self.format_number(self.q_add_l1_delta(source_q_add, reference)),
                str(sum(self.hot_counts(q_add_source, q_t_source))),
                'aggregate over displayed blocks',
            ])
        return rows, ['mode', 'variables', 'dependency blocks', 'max Q<sub>t</sub>',
                      'total Q<sub>add</sub> mass', 'L1 &Delta; vs CFG', 'hot refs', 'status'], [
            '<comment>Aggregate metrics compare dependency approximations at a glance. '
            'They are dump summaries, not a correctness ranking.</comment>'
        ]

    def source_q_add(self, q_add_source):
        result = {}
        for variable, values in q_add_source.items():
            source = self.source_name(variable)
            if source not in result:
                result[source] = [0.0 for _ in values]
            for index, value in enumerate(values):
                result[source][index] += value
        return result

    @staticmethod
    def q_add_l1_delta(left, right):
        variables = set(left) | set(right)
        total = 0.0
        for variable in variables:
            left_values = left.get(variable, [])
            right_values = right.get(variable, [])
            length = max(len(left_values), len(right_values))
            for index in range(length):
                total += abs(
                    (left_values[index] if index < len(left_values) else 0.0)
                    - (right_values[index] if index < len(right_values) else 0.0)
                )
        return total

    def algorithm_sources(self):
        return [
            ('Syntactic', self.q_add, self.q_t_syntactic),
            ('Local dependency', self.q_add_local_dependency, self.q_t_local_dependency),
            ('CFG dependency', self.q_add_cfg_dependency, self.q_t_cfg_dependency),
            ('Versioned dependency', self.q_add_versioned_dependency, self.q_t_versioned_dependency),
        ]

    def algorithm_block_masses(self):
        return [
            (label, self.block_masses(q_add_source))
            for label, q_add_source, _ in self.algorithm_sources()
        ]

    def algorithm_q_t_values(self):
        return [
            (label, q_t_source)
            for label, _, q_t_source in self.algorithm_sources()
        ]

    def block_masses(self, q_add_source):
        return [
            sum(values[block] for values in q_add_source.values() if block < len(values))
            for block in range(len(self.edges))
        ]

    def algorithm_comparison_section(self, output_dir, filename='qadd_algorithm_comparison.svg'):
        from tasks.query_cost_chart import QAddAlgorithmProfileChart

        return QAddAlgorithmProfileChart(self).section(output_dir, filename)

    def algorithm_hot_counts(self):
        return [
            (label, self.hot_counts(q_add_source, q_t_source))
            for label, q_add_source, q_t_source in self.algorithm_sources()
        ]

    def hot_counts(self, q_add_source, q_t_source):
        counts = []
        for block in range(len(self.edges)):
            q_t = q_t_source[block] if block < len(q_t_source) else 0.0
            counts.append(sum(
                1
                for values in q_add_source.values()
                if block < len(values) and q_t and values[block] > self.alpha * q_t
            ))
        return counts

    def make_table(self, q_add_source, q_t_source, status, note=None):
        rows = []
        for block in range(len(self.edges)):
            q_t = q_t_source[block] if block < len(q_t_source) else 0.0
            q_add = {variable: values[block] for variable, values in q_add_source.items() if values[block] > 0.0}
            hot = sorted([var for var, value in q_add.items() if q_t and value > self.alpha * q_t])
            rows.append([
                self.name(block),
                self.format_number(q_t),
                ', '.join(self.format_variable_key(var) for var in hot) if hot else 'None',
                self.format_counts(q_add),
                status,
            ])
        if not rows:
            rows.append(['No blocks', 0, 'None', 'None', 'not applicable'])
        notes = [note] if note else []
        return rows, ['block', 'Q<sub>t</sub>', 'hot variables', 'Q<sub>add</sub>(block, var)', 'status'], notes

    def collect_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        for block, lines in enumerate(self.lexemes):
            for line in lines:
                condition_at = SymbolicBranchDump.index_of_type(line, 5)
                goto_at = SymbolicBranchDump.index_of_type(line, 6)
                if condition_at is None or goto_at is None:
                    continue
                for token in line[condition_at + 1:goto_at]:
                    if token[0] == 0:
                        uses[block].add(token[1])
        return uses

    def collect_local_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        for block, lines in enumerate(self.lexemes):
            dependencies = {}
            for line in lines:
                assignment_at = self.assignment_operator_index(line)
                condition_at = SymbolicBranchDump.index_of_type(line, 5)
                goto_at = SymbolicBranchDump.index_of_type(line, 6)

                if assignment_at is not None:
                    target = line[assignment_at - 1]
                    if target[0] == 0:
                        dependencies[target[1]] = self.tokens_dependencies(line[assignment_at + 1:], dependencies)

                if condition_at is not None and goto_at is not None:
                    uses[block] |= self.tokens_dependencies(line[condition_at + 1:goto_at], dependencies)
        return uses

    def collect_cfg_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        in_maps = [{} for _ in self.lexemes]
        out_maps = [{} for _ in self.lexemes]
        changed = True
        while changed:
            changed = False
            for block, lines in enumerate(self.lexemes):
                next_out, block_uses = self.transfer_dependencies(in_maps[block], lines)
                uses[block] |= block_uses
                if self.dependency_maps_differ(out_maps[block], next_out):
                    out_maps[block] = next_out
                    changed = True
                for successor in self.edges[block]:
                    merged = self.merge_dependency_maps(in_maps[successor], out_maps[block])
                    if self.dependency_maps_differ(in_maps[successor], merged):
                        in_maps[successor] = merged
                        changed = True
        return uses

    def collect_versioned_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        definition_keys = self.collect_definition_keys()
        in_maps = [{} for _ in self.lexemes]
        out_maps = [{} for _ in self.lexemes]
        changed = True
        while changed:
            changed = False
            for block, lines in enumerate(self.lexemes):
                next_out, block_uses = self.transfer_versioned_dependencies(
                    in_maps[block], lines, block, definition_keys
                )
                uses[block] |= block_uses
                if self.dependency_maps_differ(out_maps[block], next_out):
                    out_maps[block] = next_out
                    changed = True
                for successor in self.edges[block]:
                    merged = self.merge_dependency_maps(in_maps[successor], out_maps[block])
                    if self.dependency_maps_differ(in_maps[successor], merged):
                        in_maps[successor] = merged
                        changed = True
        return uses

    def collect_definition_keys(self):
        counters = defaultdict(int)
        keys = {}
        for block, lines in enumerate(self.lexemes):
            for line_index, line in enumerate(lines):
                target = self.param_target(line)
                if target is None:
                    assignment_at = self.assignment_operator_index(line)
                    if assignment_at is not None and line[assignment_at - 1][0] == 0:
                        target = line[assignment_at - 1]
                if target is not None:
                    version = counters[target[1]]
                    counters[target[1]] += 1
                    keys[(block, line_index)] = (target[1], version)
        return keys

    def transfer_versioned_dependencies(self, input_map, lines, block, definition_keys):
        env = self.copy_dependency_map(input_map)
        uses = set()
        for line_index, line in enumerate(lines):
            param_target = self.param_target(line)
            if param_target is not None:
                env[param_target[1]] = {definition_keys[(block, line_index)]}

            assignment_at = self.assignment_operator_index(line)
            if assignment_at is not None:
                target = line[assignment_at - 1]
                if target[0] == 0:
                    env[target[1]] = self.versioned_tokens_dependencies(line[assignment_at + 1:], env)

            condition_at = SymbolicBranchDump.index_of_type(line, 5)
            goto_at = SymbolicBranchDump.index_of_type(line, 6)
            if condition_at is not None and goto_at is not None:
                uses |= self.versioned_tokens_dependencies(line[condition_at + 1:goto_at], env)
        return env, uses

    @staticmethod
    def param_target(line):
        for index in range(len(line) - 1):
            if line[index][0] == 2 and line[index][2] == 0 and line[index + 1][0] == 0:
                return line[index + 1]
        return None

    def transfer_dependencies(self, input_map, lines):
        env = self.copy_dependency_map(input_map)
        uses = set()
        for line in lines:
            assignment_at = self.assignment_operator_index(line)
            condition_at = SymbolicBranchDump.index_of_type(line, 5)
            goto_at = SymbolicBranchDump.index_of_type(line, 6)

            if assignment_at is not None:
                target = line[assignment_at - 1]
                if target[0] == 0:
                    env[target[1]] = self.tokens_dependencies(line[assignment_at + 1:], env)

            if condition_at is not None and goto_at is not None:
                uses |= self.tokens_dependencies(line[condition_at + 1:goto_at], env)
        return env, uses

    @staticmethod
    def copy_dependency_map(source):
        return {variable: set(dependencies) for variable, dependencies in source.items()}

    @staticmethod
    def merge_dependency_maps(left, right):
        result = HotVariableDump.copy_dependency_map(left)
        for variable, dependencies in right.items():
            result.setdefault(variable, set()).update(dependencies)
        return result

    @staticmethod
    def dependency_maps_differ(left, right):
        if left.keys() != right.keys():
            return True
        return any(left[variable] != right[variable] for variable in left)

    @staticmethod
    def assignment_operator_index(line):
        for index in range(1, len(line)):
            if line[index][0] == 2 and line[index][2] == 2:
                return index
        return None

    @classmethod
    def tokens_dependencies(cls, tokens, dependencies):
        result = set()
        for token in tokens:
            if token[0] == 0:
                result |= dependencies.get(token[1], {token[1]})
        return result

    @classmethod
    def versioned_tokens_dependencies(cls, tokens, dependencies):
        result = set()
        for token in tokens:
            if token[0] == 0:
                result |= dependencies.get(token[1], {(token[1], -1)})
        return result

    @classmethod
    def normalize_versioned_uses(cls, uses):
        return [set(cls.source_name(variable) for variable in block_uses) for block_uses in uses]

    @staticmethod
    def source_name(variable):
        if type(variable) is tuple and len(variable) == 2:
            return variable[0]
        if type(variable) is str:
            if '<sub>' in variable:
                return variable.split('<sub>', 1)[0]
            if '_' in variable and variable.rsplit('_', 1)[1].isdigit():
                return variable.rsplit('_', 1)[0]
        return variable

    @staticmethod
    def collect_variables(uses):
        return sorted(set().union(*uses) if uses else set())

    def build_q_t(self, uses):
        return self.solve_q({
            block: 1.0
            for block, block_uses in enumerate(uses)
            if block_uses
        })

    def build_q_add(self, uses, variables):
        return {
            variable: self.solve_q({
                block: 1.0 for block, block_uses in enumerate(uses) if variable in block_uses
            })
            for variable in variables
        }

    def collect_branch_successors(self):
        successors = {}
        for info in self.branch_info.branches:
            targets = []
            for target in [info['true'], info['false']]:
                if target is not None and target not in targets:
                    targets.append(target)
            if targets:
                successors[info['block']] = targets
        return successors

    def solve_q(self, cost, max_iterations=200, tolerance=0.001):
        values = [0.0 for _ in self.edges]
        for _ in range(max_iterations):
            next_values = [0.0 for _ in self.edges]
            for block in reversed(range(len(self.edges))):
                successors = sorted(self.edges[block])
                local_cost = cost.get(block, 0.0)
                if block in self.branch_successors:
                    next_values[block] = local_cost + self.beta * sum(
                        values[successor] for successor in self.branch_successors[block]
                    )
                elif len(successors) == 1:
                    next_values[block] = local_cost + values[successors[0]]
                elif successors:
                    next_values[block] = local_cost + self.beta * sum(values[successor] for successor in successors)
                else:
                    next_values[block] = 0.0
            if max(abs(next_values[idx] - values[idx]) for idx in range(len(values))) < tolerance:
                return next_values
            values = next_values
        return values

    @staticmethod
    def format_counts(counts):
        if not counts:
            return 'None'
        return ', '.join([f'{HotVariableDump.format_variable_key(var)}:{HotVariableDump.format_number(value)}'
                          for var, value in sorted(counts.items())])

    @staticmethod
    def format_variable_key(variable):
        if type(variable) is tuple and len(variable) == 2:
            name, version = variable
            if version == -1:
                return f'{escape(name)}<sub>in</sub>'
            return f'{escape(name)}<sub>{version}</sub>'
        return escape(variable)

    @staticmethod
    def format_number(value):
        if abs(value) < 0.005:
            return '0'
        return f'{value:.2f}'

