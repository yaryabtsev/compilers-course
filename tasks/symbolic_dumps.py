from collections import defaultdict, deque
from html import escape


class SymbolicBranchDump:
    def __init__(self, lexemes, edges, name):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.label_blocks = self.find_label_blocks()
        self.branches = self.find_branches()
        self.edge_conditions = self.build_edge_conditions()
        self.path_prefixes = self.collect_path_prefixes()

    def table(self):
        rows = []
        for info in self.branches:
            rows.append([
                self.name(info['block']),
                self.branch_text(info),
                self.edge_text(info['block'], info['true']),
                self.edge_text(info['block'], info['false']),
                self.format_paths(self.path_prefixes.get(info['block'], [])),
                'syntactic; no SMT feasibility check',
            ])
        if not rows:
            rows.append([
                'No conditional branches',
                'None',
                'None',
                'None',
                'true',
                'no ifTrue / ifFalse branch lines in this input',
            ])
        return rows, ['block', 'branch', 'true edge', 'false edge', 'path prefix', 'status'], [
            '<comment>Path prefixes are sampled syntactic acyclic prefixes. '
            'Cycles are cut and no SMT satisfiability check is performed.</comment>'
        ]

    def find_label_blocks(self):
        labels = {}
        for block, lines in enumerate(self.lexemes):
            if lines and lines[0] and lines[0][0][0] == 1:
                labels[lines[0][0][1]] = block
        return labels

    def find_branches(self):
        branches = []
        for block, lines in enumerate(self.lexemes):
            for line in lines:
                condition_at = self.index_of_type(line, 5)
                goto_at = self.index_of_type(line, 6)
                if condition_at is None or goto_at is None:
                    continue
                target = self.goto_target(line, goto_at)
                fallthrough = self.fallthrough(block, target)
                is_true_jump = line[condition_at][1]
                condition = self.format_expression(line[condition_at + 1:goto_at])
                true_target = target if is_true_jump else fallthrough
                false_target = fallthrough if is_true_jump else target
                branches.append({
                    'block': block,
                    'line': line,
                    'condition': condition or 'true',
                    'jump_kind': 'ifTrue' if is_true_jump else 'ifFalse',
                    'target': target,
                    'fallthrough': fallthrough,
                    'true': true_target,
                    'false': false_target,
                })
        return branches

    def build_edge_conditions(self):
        edge_conditions = {}
        for info in self.branches:
            condition = info['condition']
            if info['true'] is not None:
                edge_conditions[(info['block'], info['true'])] = condition
            if info['false'] is not None:
                edge_conditions[(info['block'], info['false'])] = self.negate(condition)
        return edge_conditions

    def collect_path_prefixes(self, max_paths=3):
        prefixes = defaultdict(list)
        seen_prefixes = defaultdict(set)
        if not self.edges:
            return prefixes
        queue = deque([(0, tuple(), (0,))])
        prefixes[0].append(tuple())
        seen_prefixes[0].add(tuple())
        max_depth = max(2, len(self.edges) + 1)
        while queue:
            block, conditions, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for successor in sorted(self.edges[block]):
                edge_condition = self.edge_condition(block, successor)
                next_conditions = conditions
                if edge_condition != 'true':
                    next_conditions = conditions + (edge_condition,)
                if next_conditions not in seen_prefixes[successor] and len(prefixes[successor]) < max_paths:
                    prefixes[successor].append(next_conditions)
                    seen_prefixes[successor].add(next_conditions)
                if successor not in path and len(prefixes[successor]) <= max_paths:
                    queue.append((successor, next_conditions, path + (successor,)))
        return prefixes

    def edge_condition(self, source, target):
        return self.edge_conditions.get((source, target), 'true')

    def edge_text(self, source, target):
        if target is None:
            return 'None'
        return f'{self.name(source)} &rarr; {self.name(target)}'

    def branch_text(self, info):
        return f'{info["jump_kind"]} {info["condition"]} goto {self.block_ref(info["target"])}'

    @staticmethod
    def negate(condition):
        if condition.startswith('&not;(') and condition.endswith(')'):
            return condition[6:-1]
        return f'&not;({condition})'

    def block_ref(self, block):
        return self.name(block) if block is not None else 'None'

    @staticmethod
    def format_paths(paths):
        if not paths:
            return 'true'
        formatted = []
        for path in paths:
            if path:
                formatted.append(' &and; '.join(path))
            else:
                formatted.append('true')
        return '<br>'.join(formatted)

    def fallthrough(self, block, target):
        expected = block + 1
        if expected < len(self.edges) and expected in self.edges[block]:
            return expected
        for successor in sorted(self.edges[block]):
            if successor != target:
                return successor
        return None

    def goto_target(self, line, goto_at):
        if goto_at + 1 >= len(line) or line[goto_at + 1][0] != 1:
            return None
        return self.label_blocks.get(line[goto_at + 1][1])

    @staticmethod
    def index_of_type(line, token_type):
        for index, token in enumerate(line):
            if token[0] == token_type:
                return index
        return None

    @classmethod
    def format_expression(cls, tokens):
        parts = []
        for token in tokens:
            if token[0] == 1:
                continue
            parts.append(cls.format_token(token))
        return ' '.join(part for part in parts if part)

    @staticmethod
    def format_token(token):
        kind = token[0]
        if kind == 0:
            name = escape(token[1])
            indexes = token[2]
            if type(indexes) is int:
                return f'{name}<sub>{indexes}</sub>'
            if type(indexes) is list and len(indexes) == 1:
                return f'{name}<sub>{indexes[0]}</sub>'
            return name
        if kind == 1:
            return escape(token[1])
        if kind == 2:
            if token[2] == 5:
                return f'%{escape(token[1])}'
            return escape(token[1])
        if kind == 3:
            return f'#{token[1]}'
        if kind == 4:
            return f'@{escape(token[1])}'
        if kind == 5:
            return 'ifTrue' if token[1] else 'ifFalse'
        if kind == 6:
            return 'goto'
        if kind == 7:
            return 'pass'
        return escape(str(token))


class JoinMergePreview:
    def __init__(self, phi, dominator, name):
        self.phi = phi
        self.dominator = dominator
        self.name = name

    def table(self):
        rows = []
        for block in range(self.dominator.N):
            preds = sorted(self.dominator.pred_list[block])
            if len(preds) < 2:
                continue
            variables = sorted(self.phi.phi_args[block])
            if not variables:
                rows.append([
                    self.name(block),
                    self.format_blocks(preds),
                    'None',
                    'No phi variables placed at this join.',
                    'structural join only',
                ])
                continue
            for variable in variables:
                rows.append(self.variable_row(block, preds, variable))
        if not rows:
            rows.append([
                'No join candidates',
                'None',
                'None',
                'No blocks with multiple predecessors.',
                'not applicable',
            ])
        return rows, ['join', 'predecessors', 'variable', 'merge preview', 'status'], [
            '<comment>Merge previews are display-only. They reuse predecessor and phi data; '
            'no symbolic store is executed and no path feasibility is checked.</comment>'
        ]

    def variable_row(self, block, preds, variable):
        mapping = self.phi.phi_pred_args.get((block, variable), {})
        pairs = []
        for pred in preds:
            if pred in mapping:
                pairs.append((pred, self.version(variable, mapping[pred])))
        status = 'predecessor-mapped; no SMT check'
        if len(pairs) != len(preds):
            visible = self.visible_phi_args(block, variable)
            pairs = [(pred, value) for pred, value in zip(preds, visible)]
            status = 'partial; predecessor mapping incomplete'
        merge = self.nested_ite(pairs) if pairs else 'None'
        summary = self.value_summary(pairs) if pairs else 'None'
        return [
            self.name(block),
            self.format_blocks(preds),
            variable,
            f'{merge}<br>{summary}',
            status,
        ]

    def visible_phi_args(self, block, variable):
        for line_index, line in enumerate(self.phi.code_blocks[block]):
            if not self.phi.is_phi_line(block, line_index):
                break
            if line[-1][1] == variable:
                return [self.version(variable, index) for index in self.phi.indexes(line[-1])]
        return []

    def nested_ite(self, pairs):
        if len(pairs) == 1:
            return pairs[0][1]
        result = pairs[-1][1]
        for pred, value in reversed(pairs[:-1]):
            result = f'ite(path({self.name(pred)}), {value}, {result})'
        return result

    def value_summary(self, pairs):
        entries = [f'(path({self.name(pred)}), {value})' for pred, value in pairs]
        return '{' + ', '.join(entries) + '}'

    @staticmethod
    def version(variable, index):
        return f'{escape(variable)}<sub>{index}</sub>'

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'


class HotVariableDump:
    def __init__(self, lexemes, edges, name, alpha=0.35):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.alpha = alpha
        self.branch_uses = self.collect_branch_uses()

    def table(self):
        rows = []
        for block in range(len(self.edges)):
            counts = self.future_counts(block)
            total = sum(counts.values())
            hot = sorted([var for var, count in counts.items() if total and count > self.alpha * total])
            rows.append([
                self.name(block),
                total,
                ', '.join(hot) if hot else 'None',
                self.format_counts(counts),
                'syntactic QCE-style approximation; no SMT or ite-cost model',
            ])
        if not rows:
            rows.append(['No blocks', 0, 'None', 'None', 'not applicable'])
        return rows, ['block', 'future branch uses', 'hot variables', 'counts', 'status'], [
            '<comment>Hot variables approximate QCE by counting future syntactic uses in branch conditions. '
            'The dump does not estimate solver query cost.</comment>'
        ]

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

    def future_counts(self, block):
        counts = defaultdict(int)
        for node in self.reachable_from(block):
            for variable in self.branch_uses[node]:
                counts[variable] += 1
        return counts

    def reachable_from(self, block):
        seen = set()
        stack = [block]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(sorted(self.edges[node] - seen, reverse=True))
        return seen

    @staticmethod
    def format_counts(counts):
        if not counts:
            return 'None'
        return ', '.join([f'{escape(var)}:{count}' for var, count in sorted(counts.items())])


class UnsupportedSymbolicStageDump:
    def table(self):
        rows = [
            ['Array transformations', 'stub',
             'current MIR has no array read/write syntax or array values',
             'keep as documentation-only placeholder'],
            ['Function summaries', 'stub',
             'current MIR has param/return but no call instruction, callee identity, or call graph',
             'keep as documentation-only placeholder'],
            ['Heap/list/shape execution', 'out of scope',
             'current MIR has no heap allocation, fields, references, aliases, or predicates',
             'do not expand parser for this dump-first task'],
            ['Compiled symbolic execution', 'out of scope',
             'project is not compiling LLVM/C/Java into a symbolic executor',
             'no implementation planned'],
        ]
        return rows, ['family', 'status', 'why unavailable', 'current action'], [
            '<comment>These paper families are intentionally marked as stubs or out of scope until the input '
            'language already supports the required concepts.</comment>'
        ]


class AcyclicRegionSummaryPreview:
    def __init__(self, lexemes, edges, post_dominator, name):
        self.lexemes = lexemes
        self.edges = edges
        self.post_dominator = post_dominator
        self.name = name
        self.branches = SymbolicBranchDump(lexemes, edges, name)

    def table(self):
        rows = []
        for branch in self.branches.branches:
            entry = branch['block']
            if entry >= len(self.post_dominator.ipdom_list):
                continue
            exit_block = self.post_dominator.ipdom_list[entry]
            if exit_block in (-1, entry):
                continue
            nodes = self.region_nodes(entry, exit_block)
            if not nodes:
                continue
            cyclic = self.has_cycle(nodes)
            preview = self.path_preview(entry, exit_block, nodes) if not cyclic else 'not emitted'
            status = ('syntactic acyclic summary; no SMT/store execution'
                      if not cyclic else 'cycle detected; transition: incomplete loop / resume normal dump')
            rows.append([
                self.name(entry),
                self.name(exit_block),
                self.format_blocks(sorted(nodes)),
                not cyclic,
                preview,
                status,
            ])
        if not rows:
            rows.append([
                'No acyclic region candidates',
                'None',
                'None',
                False,
                'None',
                'no conditional block with a usable immediate postdominator',
            ])
        return rows, ['entry', 'exit', 'nodes', 'loop-free', 'path summary preview', 'status'], [
            '<comment>Region summaries are syntactic previews inspired by veritesting-style regions. '
            'They do not execute stores, solve formulas, or replace the existing region reduction.</comment>'
        ]

    def region_nodes(self, entry, exit_block):
        nodes = set()
        stack = [entry]
        while stack:
            node = stack.pop()
            if node == exit_block or node in nodes:
                continue
            nodes.add(node)
            for successor in sorted(self.edges[node]):
                if successor != exit_block:
                    stack.append(successor)
        return nodes

    def has_cycle(self, nodes):
        visiting = set()
        visited = set()

        def visit(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for successor in self.edges[node]:
                if successor in nodes and visit(successor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in sorted(nodes))

    def path_preview(self, entry, exit_block, nodes, max_paths=4):
        paths = []

        def walk(node, conditions, seen):
            if len(paths) >= max_paths:
                return
            if node == exit_block:
                paths.append(conditions)
                return
            if node in seen:
                return
            next_seen = seen | {node}
            for successor in sorted(self.edges[node]):
                if successor != exit_block and successor not in nodes:
                    continue
                condition = self.branches.edge_condition(node, successor)
                next_conditions = conditions
                if condition != 'true':
                    next_conditions = conditions + [condition]
                walk(successor, next_conditions, next_seen)

        walk(entry, [], set())
        if not paths:
            return 'no acyclic path preview'
        formatted = []
        for index, conditions in enumerate(paths, start=1):
            path_condition = ' &and; '.join(conditions) if conditions else 'true'
            formatted.append(f'path {index}: {path_condition} &rarr; {self.name(exit_block)}')
        if len(paths) == max_paths:
            formatted.append('path list truncated')
        return '<br>'.join(formatted)

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'
