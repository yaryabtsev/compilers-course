from tasks.branch_conditions import SymbolicBranchDump


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
            path_count = self.path_count(entry, exit_block, nodes) if not cyclic else 0
            preview = self.path_preview(entry, exit_block, nodes) if not cyclic else 'not emitted'
            status = ('syntactic acyclic summary; no SMT/store execution'
                      if not cyclic else 'cycle detected; transition: incomplete loop / resume normal dump')
            rows.append([
                self.name(entry),
                self.name(exit_block),
                self.format_blocks(sorted(nodes)),
                not cyclic,
                str(path_count),
                preview,
                status,
            ])
        if not rows:
            rows.append([
                'No acyclic region candidates',
                'None',
                'None',
                False,
                '0',
                'None',
                'no conditional block with a usable immediate postdominator',
            ])
        return rows, ['entry', 'exit', 'nodes', 'loop-free', 'paths shown',
                      'path summary preview', 'status'], [
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

    def path_count(self, entry, exit_block, nodes, max_paths=4):
        count = 0

        def walk(node, seen):
            nonlocal count
            if count >= max_paths:
                return
            if node == exit_block:
                count += 1
                return
            if node in seen:
                return
            next_seen = seen | {node}
            for successor in sorted(self.edges[node]):
                if successor == exit_block or successor in nodes:
                    walk(successor, next_seen)

        walk(entry, set())
        return count

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
