import copy


class LocalOptimization:
    def __init__(self, block):
        self.block = block
        self.variables = []
        self.table = []

    def make_table(self) -> (list, list):
        new_block = []
        for line in self.block:
            idx = 0
            new_block.append(copy.deepcopy(line))
            while idx < len(line) and (line[idx][0] != 2 or line[idx][2] != 2):
                idx += 1
            if idx == len(line):
                for var in new_block[-1]:
                    if var[0] == 0:
                        self.find(var[1])
                        var[2].append(self.last_index(var[1])[0])
            elif line[idx][2] == 2:
                if line[idx - 1][0] == 0:
                    line[idx - 1][3] = True
                else:
                    raise Exception(f'Not recognized line: {line}.')
                for var in new_block[-1][idx:]:
                    if var[0] == 0:
                        self.find(var[1])
                        var[2].append(self.last_index(var[1])[0])
                if line[idx + 1][0] == 2 and line[idx + 1][2] in [3, 5]:
                    key = [line[idx + 1][1], *[self.find(i[1]) for i in line[idx:] if i[0] in [0, 3]]]
                    self.key_append(key, line[idx - 1][1])
                elif line[idx + 1][0] in [0, 3]:
                    self.table[self.find(line[idx + 1][1]) - 1][-1].append(
                        [line[idx - 1][1], self.last_index(line[idx - 1][1])[0] + 1])
                new_block[-1][idx - 1][2].append(self.last_index(line[idx - 1][1])[0])
        # TODO: 4 optimizations
        return new_block, self.table

    def find(self, var: str) -> int:
        _, row = self.last_index(var)
        if row == 0:
            self.table.append(['id/nm', [[var, 0]]])
            return len(self.table)
        return row

    def last_index(self, var: str) -> (int, int):
        idx, row = -1, -1
        for i in range(len(self.table)):
            for _var in self.table[i][-1]:
                if _var[0] == var:
                    if idx < _var[1]:
                        idx, row = _var[1], i
        return idx, row + 1

    def key_append(self, key: list, var: str) -> None:
        idx = self.last_index(var)[0] + 1
        for row in self.table:
            if key == row[:-1]:
                row[-1].append([var, idx])
                return
        self.table.append([*key, [[var, idx]]])
