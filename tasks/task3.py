import copy
from collections import defaultdict


class Phi:
    def __init__(self, code_blocks, graph):
        self.graph = graph
        self.code_blocks = []
        self.N = len(code_blocks)
        for i in range(self.N):
            if not graph.available[i]:
                self.code_blocks.append([])
            else:
                self.code_blocks.append(copy.deepcopy(code_blocks[i]))
        self.globs = set()
        self.blocks = defaultdict(set)
        self.phi_args = [set() for _ in range(self.N)]
        self.phis: list
        self.counter = defaultdict(int)
        self.stack = defaultdict(list)

    def globals_blocks(self):
        spoiler = []
        line_num = 1
        for node in range(self.N):
            spoiler += [['tab', 0], ['block', node], '<gb1>-block:</gb1>']
            def_block = set()
            spoiler += [['tab', 1], '<gb2>def<sub>',
                        ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', copy.deepcopy(def_block)]]
            for line in self.code_blocks[node]:
                spoiler += [['tab', 2], ['line', [line], line_num]]
                for word in line:
                    if word[0] == 0 and not word[3] and word[1] not in def_block:
                        spoiler += [['tab', 3], '<gb3>Globals&nbsp;:&nbsp;</gb3>',
                                    ['set', copy.deepcopy(self.globs)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {word[1]}]]
                        self.globs.add(word[1])
                for word in line:
                    if word[0] == 0 and word[3]:
                        spoiler += [['tab', 3], '<gb2>def<sub>',
                                    ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', copy.deepcopy(def_block)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {word[1]}]]
                        def_block.add(word[1])
                        spoiler += [['tab', 3], '<gb4>Blocks(<gb5>', word[1], '</gb5>)&nbsp;:&nbsp;</gb4>',
                                    ['block-set', copy.deepcopy(self.blocks[word[1]])],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['block-set', {node}]]
                        self.blocks[word[1]].add(node)

                line_num += 1
        return spoiler[1:]

    def locate(self) -> list:
        # TODO: insert phi-functions in self.code_blocks
        spoiler = []
        for var in self.globs:
            spoiler += [['tab', 0], f'<l1>variable</l1>&nbsp;<w0>{var}</w0>:']
            work_list = list(self.blocks[var])
            spoiler += [['tab', 1], '<l2>WorkList</l2> : ', ['block-set', copy.deepcopy(work_list)]]
            item = 0
            n = len(work_list)
            while item < n:
                for df in self.graph.df_list[work_list[item]]:
                    if var not in self.phi_args[df]:
                        spoiler += [['tab', 1], '<l3>insert</l3>&nbsp;', ['phi', f'{var}'],
                                    '&nbsp;in&nbsp;', ['block', df], '<gb1>-block:</gb1>']
                        self.phi_args[df].add(var)
                    if df not in work_list:
                        spoiler += [['tab', 1], '<l2>WorkList</l2> : ', ['block-set', copy.deepcopy(work_list)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {df}]]
                        work_list.append(df)
                        n += 1
                item += 1
        self.phis = [{var: [0, []] for var in sorted(self.phi_args[block])} for block in range(self.graph.N)]
        return spoiler[1:]

    def table_new_phi(self):
        columns = ["block ="] + list(range(self.N))
        table = []
        for var in sorted(self.blocks):
            row = [var]
            for i in range(self.N):
                if var in self.phi_args[i]:
                    row.append(True)
                else:
                    row.append(False)
            table.append(row)
        return table, columns

    def rename(self, block: int, tabs: int = 0) -> list:
        new_block = []
        spoiler = [['tab', tabs], '<r1>Rename(', ['block', block], ')</r1>:']
        self.rename_phi(block, tabs, spoiler)
        new_block += self.rename_instructions(block, tabs, spoiler)
        for successor in self.graph.edges[block]:
            self.fill(successor, tabs, spoiler)
        for successor in self.graph.dom_edges[block]:
            spoiler += self.rename(successor, tabs + 1)
            spoiler += [['tab', tabs + 2], '<r2>return to ', ['block', block], ';</r2>']
        # show_table(self.stack_table())
        self.clean(block, tabs, spoiler)
        # show_table(self.stack_table())
        self.code_blocks[block] = new_block
        return spoiler

    def table_gb(self):
        columns = ["var ="] + sorted(self.blocks)
        table = []
        row = ["Blocks(var)"]
        for var in columns[1:]:
            if self.blocks[var]:
                row.append(self.blocks[var])
            else:
                row.append('None')
        table.append(row)
        row = ["is Global"]
        for var in columns[1:]:
            row.append(var in self.globs)
        table.append(row)
        return table, columns

    def rename_phi(self, block, tabs, spoiler):
        # TODO: rename_phi()
        pass

    def rename_instructions(self, block, tabs, spoiler) -> list:
        # TODO: rename_instructions()
        return []

    def clean(self, block, tabs, spoiler):
        # TODO: clean()
        pass

    def fill(self, successor, tabs, spoiler):
        # TODO: fill()
        pass
