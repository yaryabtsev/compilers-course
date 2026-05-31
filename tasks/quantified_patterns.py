from html import escape

from tasks.branch_conditions import SymbolicBranchDump
from tasks.query_cost_estimation import HotVariableDump


class QuantifiedPatternPreview:
    def __init__(self, lexemes, edges, name, max_depth=4):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.max_depth = max_depth
        self.branches = SymbolicBranchDump(lexemes, edges, name)
        self.branch_by_block = {branch['block']: branch for branch in self.branches.branches}
        self.back_edges = self.find_back_edges()

    def tables(self):
        return [
            ('Bounded node tree', *self.node_tree_table()),
            ('Pattern inference', *self.pattern_table()),
            ('Automaton walkthrough', *self.automaton_table()),
        ]

    def find_back_edges(self):
        return [
            (source, target)
            for source, successors in enumerate(self.edges)
            for target in sorted(successors)
            if target <= source
        ]

    def node_tree_table(self):
        rows = []
        for latch, header in self.back_edges:
            nodes = self.loop_nodes(header, latch)
            loop_name = f'{self.name(header)} &larr; {self.name(latch)}'
            self.walk_tree(rows, loop_name, header, nodes, 'loop header', 0, ())
        if not rows:
            rows.append(['No loop back edges', '0', 'None', 'None', 'None',
                         'no quantified-pattern candidate'])
        return rows, ['loop', 'depth', 'node', 'via condition', 'children', 'inferred role'], [
            '<comment>The node tree is a bounded syntactic preview. It expands simple loop candidates only to a '
            'small depth, cuts cycles, and does not build quantified solver formulas.</comment>'
        ]

    def walk_tree(self, rows, loop_name, node, nodes, incoming, depth, path):
        successors = sorted(self.edges[node])
        rows.append([
            loop_name,
            str(depth),
            self.name(node),
            incoming,
            self.format_blocks(successors),
            self.node_role(node),
        ])
        if depth >= self.max_depth:
            return
        for successor in successors:
            if successor in path:
                continue
            if successor not in nodes:
                continue
            condition = self.branches.edge_condition(node, successor)
            self.walk_tree(rows, loop_name, successor, nodes, condition, depth + 1, path + (node,))

    def pattern_table(self):
        rows = []
        for latch, header in self.back_edges:
            nodes = self.loop_nodes(header, latch)
            loop_name = f'{self.name(header)} &larr; {self.name(latch)}'
            guard = self.loop_guard(header, nodes)
            induction = self.induction_update(nodes, latch)
            accumulator = self.accumulator_update(nodes, induction)
            rows.append([
                loop_name,
                'loop guard',
                self.name(header),
                guard or 'not inferred',
                'guarded loop candidate' if guard else 'missing branch guard',
            ])
            rows.append([
                loop_name,
                'induction update',
                self.name(latch),
                self.format_induction(induction),
                'linear + constant update' if induction else 'not inferred',
            ])
            if accumulator:
                rows.append([
                    loop_name,
                    'guarded accumulator',
                    accumulator['blocks'],
                    accumulator['schema'],
                    'one-level branch/update pattern',
                ])
            else:
                rows.append([
                    loop_name,
                    'guarded accumulator',
                    'None',
                    'not inferred',
                    'requires two branch arms updating the same variable',
                ])
            rows.append([
                loop_name,
                'quantified sketch',
                self.name(header),
                self.quantified_schema(guard, induction, accumulator),
                'report-level formula; not emitted to a solver',
            ])
        if not rows:
            rows.append(['No loop back edges', 'None', 'None', 'None',
                         'no quantified-pattern candidate'])
        return rows, ['loop', 'pattern', 'evidence', 'inferred sketch', 'status'], [
            '<comment>Pattern inference is intentionally narrow: one loop guard, one linear induction update, '
            'and one direct two-arm accumulator update. It is meant for readable dumps, not complete quantified '
            'state merging.</comment>'
        ]

    def loop_nodes(self, header, latch):
        return {
            node
            for node in range(len(self.edges))
            if self.reachable(header, node) and self.reachable(node, latch)
        }

    def reachable(self, start, target):
        stack = [start]
        seen = set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(sorted(self.edges[node] - seen))
        return False

    def loop_guard(self, header, nodes):
        branch = self.branch_by_block.get(header)
        if not branch:
            return None
        if branch['true'] in nodes and branch['false'] not in nodes:
            return branch['condition']
        if branch['false'] in nodes and branch['true'] not in nodes:
            return SymbolicBranchDump.negate(branch['condition'])
        return branch['condition']

    def induction_update(self, nodes, latch):
        candidates = []
        for block in sorted(nodes):
            for _, target, delta, text in self.assignment_deltas(block):
                candidates.append((block, target, delta, text))
        for block, target, delta, text in candidates:
            if block == latch:
                return block, target, delta, text
        return candidates[0] if candidates else None

    def accumulator_update(self, nodes, induction):
        induction_var = induction[1] if induction else None
        for branch in self.branches.branches:
            block = branch['block']
            if block not in nodes:
                continue
            true_updates = self.assignment_deltas(branch['true']) if branch['true'] in nodes else []
            false_updates = self.assignment_deltas(branch['false']) if branch['false'] in nodes else []
            for _, true_target, true_delta, true_text in true_updates:
                for _, false_target, false_delta, false_text in false_updates:
                    if true_target != false_target or true_target == induction_var:
                        continue
                    condition = branch['condition']
                    schema = (
                        f'{escape(true_target)} += '
                        f'ite({self.indexed_condition(condition, induction_var)}, '
                        f'{true_delta}, {false_delta}) per iteration'
                    )
                    return {
                        'branch': branch['block'],
                        'condition': condition,
                        'blocks': f'{self.name(branch["true"])} / {self.name(branch["false"])}',
                        'schema': schema,
                        'target': true_target,
                        'true_block': branch['true'],
                        'false_block': branch['false'],
                        'true_delta': true_delta,
                        'false_delta': false_delta,
                        'updates': f'{true_text}; {false_text}',
                    }
        return None

    def automaton_table(self):
        rows = []
        for latch, header in self.back_edges:
            nodes = self.loop_nodes(header, latch)
            loop_name = f'{self.name(header)} &larr; {self.name(latch)}'
            guard = self.loop_guard(header, nodes)
            induction = self.induction_update(nodes, latch)
            accumulator = self.accumulator_update(nodes, induction)
            rows.extend(self.automaton_rows(loop_name, header, latch, guard, induction, accumulator))
        if not rows:
            rows.append(['No loop back edges', 'S0', 'scan', 'None', 'None',
                         'no loop candidate', 'reject', 'no quantified-pattern candidate'])
        return rows, ['loop', 'state', 'case', 'node', 'condition',
                      'action', 'next', 'status'], [
            '<comment>This is a finite-state walkthrough of the recognized shape. It simulates a few structural '
            'cases from the loop tree: exit, true arm, false arm, latch/repeat, and accept. It is not a full '
            'execution tree and does not prove regularity for arbitrary inputs.</comment>'
        ]

    def automaton_rows(self, loop_name, header, latch, guard, induction, accumulator):
        rows = []
        rows.append([
            loop_name,
            'S0',
            'loop exits before next iteration',
            self.name(header),
            SymbolicBranchDump.negate(guard) if guard else 'no guard',
            'emit terminal leaf for current k',
            'ACCEPT-EXIT' if guard else 'REJECT',
            'terminal case similar to a leaf in the execution tree',
        ])
        rows.append([
            loop_name,
            'S0',
            'loop continues',
            self.name(header),
            guard or 'no guard',
            'enter loop body for iteration k',
            'S1' if guard else 'REJECT',
            'guard accepted' if guard else 'missing loop guard',
        ])

        if accumulator:
            rows.append([
                loop_name,
                'S1',
                'inner true arm',
                self.name(accumulator['branch']),
                accumulator['condition'],
                f'{escape(accumulator["target"])} += {accumulator["true_delta"]}',
                'S2',
                f'arm block {self.name(accumulator["true_block"])}',
            ])
            rows.append([
                loop_name,
                'S1',
                'inner false arm',
                self.name(accumulator['branch']),
                SymbolicBranchDump.negate(accumulator['condition']),
                f'{escape(accumulator["target"])} += {accumulator["false_delta"]}',
                'S2',
                f'arm block {self.name(accumulator["false_block"])}',
            ])
        else:
            rows.append([
                loop_name,
                'S1',
                'inner branch',
                'None',
                'not inferred',
                'no two-arm accumulator update found',
                'REJECT',
                'pattern incomplete',
            ])

        if induction:
            _, variable, delta, text = induction
            sign = '+' if delta >= 0 else '-'
            rows.append([
                loop_name,
                'S2',
                'latch / repeat',
                self.name(latch),
                'after either arm',
                f'{text}; k := k + 1',
                'S0',
                f'{escape(variable)} advances {sign} {abs(delta)}',
            ])
        else:
            rows.append([
                loop_name,
                'S2',
                'latch / repeat',
                self.name(latch),
                'after either arm',
                'no linear induction update found',
                'REJECT',
                'pattern incomplete',
            ])

        if guard and induction and accumulator:
            rows.append([
                loop_name,
                'ACCEPT',
                'regular family',
                self.name(header),
                'guard + branch arms + latch',
                self.quantified_schema(guard, induction, accumulator),
                'merged schema',
                'accepted bounded approximation',
            ])
        return rows

    def quantified_schema(self, guard, induction, accumulator):
        if not (guard and induction and accumulator):
            return 'not inferred'
        _, variable, delta, _ = induction
        iterator = 'k'
        range_hint = self.range_hint(guard, variable, delta, iterator)
        return f'for {iterator} in {range_hint}: {accumulator["schema"]}'

    @staticmethod
    def range_hint(guard, variable, delta, iterator):
        if not variable:
            return 'loop iterations'
        if f'{escape(variable)} &lt; ' in guard:
            bound = guard.split('&lt;', 1)[1].strip()
            return f'[{escape(variable)}<sub>0</sub>, {bound})'
        direction = '+' if delta >= 0 else '-'
        return f'{iterator} over {escape(variable)} {direction} {abs(delta)}'

    @staticmethod
    def indexed_condition(condition, variable):
        if not variable:
            return condition
        needle = escape(variable)
        return ' '.join('k' if part == needle else part for part in condition.split(' '))

    def assignment_deltas(self, block):
        if block is None or block < 0 or block >= len(self.lexemes):
            return []
        result = []
        for line in self.lexemes[block]:
            parsed = self.assignment_delta(line)
            if parsed:
                target, delta = parsed
                result.append((block, target, delta, self.assignment_text(line)))
        return result

    @staticmethod
    def assignment_delta(line):
        assignment_at = HotVariableDump.assignment_operator_index(line)
        if assignment_at is None or assignment_at < 1:
            return None
        target = line[assignment_at - 1]
        if target[0] != 0:
            return None
        rhs = line[assignment_at + 1:]
        if len(rhs) < 3 or rhs[0][0] != 2 or rhs[0][2] != 3:
            return None
        op = rhs[0][1]
        if op not in ['+', '-']:
            return None
        if rhs[1][0] == 0 and rhs[1][1] == target[1] and rhs[2][0] == 3:
            return target[1], rhs[2][1] if op == '+' else -rhs[2][1]
        if op == '+' and rhs[1][0] == 3 and rhs[2][0] == 0 and rhs[2][1] == target[1]:
            return target[1], rhs[1][1]
        return None

    @staticmethod
    def assignment_text(line):
        assignment_at = HotVariableDump.assignment_operator_index(line)
        if assignment_at is None or assignment_at < 1:
            return SymbolicBranchDump.format_expression(line)
        target = SymbolicBranchDump.format_token(line[assignment_at - 1])
        rhs = SymbolicBranchDump.format_expression(line[assignment_at + 1:])
        return f'{target} = {rhs}'

    def node_role(self, node):
        branch = self.branch_by_block.get(node)
        if branch:
            return f'branch: {branch["condition"]}'
        updates = [text for _, _, _, text in self.assignment_deltas(node)]
        if updates:
            return '; '.join(updates)
        return 'linear block'

    def format_induction(self, induction):
        if not induction:
            return 'not inferred'
        _, variable, delta, text = induction
        sign = '+' if delta >= 0 else '-'
        return f'{text}; {escape(variable)} := {escape(variable)} {sign} {abs(delta)}'

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'


