import copy


class Phi:
    def __init__(self, code_blocks, graph):
        self.graph = graph
        self.code_blocks = copy.deepcopy(code_blocks)
