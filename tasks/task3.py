import copy
from collections import defaultdict


class Phi:
    def __init__(self, code_blocks, graph):
        self.graph = graph
        self.code_blocks = copy.deepcopy(code_blocks)
        self.N = len(self.code_blocks)
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

    def locate(self):
        pass

    def table_new_phi(self):
        pass

    def rename(self, param):
        pass

    def add_phi(self):
        pass
