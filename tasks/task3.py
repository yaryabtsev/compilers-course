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

    def globals_blocks(self):
        spoiler = []
        line_num = 1
        for node in range(self.N):
            spoiler += [['tab', 0], ['block', node], '<gb1>-block:</gb1>']
            def_block = set()
            spoiler += [['tab', 1], '<gb2>def<sub>',
                        ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', def_block]]
            for line in self.code_blocks[node]:
                spoiler.append([['tab', 2], ['line', [line], line_num]])
                for word in line:
                    if word[0] == 0 and not word[3] and word[1] not in def_block:
                        self.globs.add(word[1])
                        spoiler += [['tab', 3], '<gb3>Globals&nbsp;:&nbsp;</gb3>',
                                    ['set', self.globs]]
                for word in line:
                    if word[0] == 0 and word[3]:
                        def_block.add(word[1])
                        spoiler += [['tab', 3], '<gb2>def<sub>',
                                    ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', def_block]]
                        self.blocks[word[1]].add(node)
                        spoiler += [['tab', 3], '<gb4>Blocks(<gb5>', word[1], '</gb5>)&nbsp;:&nbsp;</gb4>',
                                    ['block-set', self.blocks[word[1]]]]
                line_num += 1
        return spoiler[1:]

    def locate(self) -> list:
        spoiler = []
        for var in self.globs:
            spoiler += [['tab', 0], f'<l1>variable</l1>&nbsp;<w0>{var}</w0>:']
            work_list = list(self.blocks[var])
            spoiler += [['tab', 1], '<l2>WorkList<l2>', ['block-set', work_list]]
            item = 0
            n = len(work_list)
            while item < n:
                for df in self.graph.df_list[work_list[item]]:
                    if var not in self.phi_args[df]:
                        spoiler += [['tab', 1], '<l3>insert<l3>&nbsp;', ['phi', f'*{var}'],
                                    '&nbsp;in&nbsp;', ['block', df], '<gb1>-block:</gb1>']
                        self.phi_args[df].add(var)
                    if df not in work_list:
                        work_list.append(df)
                        spoiler += [['tab', 1], '<l2>WorkList<l2>', ['block-set', work_list]]
                        n += 1
                item += 1
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

    def rename(self, param):
        pass

    def add_phi(self):
        pass

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
