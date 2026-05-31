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
            prefixes = self.path_prefixes.get(info['block'], [])
            rows.append([
                self.name(info['block']),
                self.branch_text(info),
                self.format_symbols(info['symbols']),
                self.edge_text(info['block'], info['true']),
                self.edge_text(info['block'], info['false']),
                str(len(prefixes)),
                self.format_paths(prefixes),
                'syntactic; no SMT feasibility check',
            ])
        if not rows:
            rows.append([
                'No conditional branches',
                'None',
                'None',
                'None',
                'None',
                '0',
                'true',
                'no ifTrue / ifFalse branch lines in this input',
            ])
        return rows, ['block', 'branch', 'condition symbols', 'true edge', 'false edge',
                      'prefixes shown', 'path prefix', 'status'], [
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
                condition_tokens = line[condition_at + 1:goto_at]
                condition = self.format_expression(condition_tokens)
                true_target = target if is_true_jump else fallthrough
                false_target = fallthrough if is_true_jump else target
                branches.append({
                    'block': block,
                    'line': line,
                    'condition': condition or 'true',
                    'symbols': self.condition_symbols(condition_tokens),
                    'jump_kind': 'ifTrue' if is_true_jump else 'ifFalse',
                    'target': target,
                    'fallthrough': fallthrough,
                    'true': true_target,
                    'false': false_target,
                })
        return branches

    @staticmethod
    def condition_symbols(tokens):
        symbols = set()
        for token in tokens:
            if token[0] == 0:
                symbols.add(escape(token[1]))
            elif token[0] == 4:
                symbols.add(f'@{escape(token[1])}')
        return sorted(symbols)

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

    @staticmethod
    def format_symbols(symbols):
        return ', '.join(symbols) if symbols else 'None'

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


