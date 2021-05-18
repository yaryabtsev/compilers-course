import re


class Parser:
    def __init__(self, code: list):
        self.code = code
        self.blocks = [[]]
        self.lexemes = []
        self.N = len(self.blocks)
        self.edges = []

    def split_blocks(self):
        block = []
        self.code.append('\n')
        n = len(self.code)
        for i in range(n):
            code_line = re.sub(r'\s+', ' ', self.code[i])
            if not code_line:
                continue
            while (i == n - 1 and self.blocks[-1]) or (block and (
                    ':' in code_line or 'goto' in block[-1]
                    or 'return' in block[-1] or 'if' in block[-1])):
                self.blocks.append(block)
                block, lex_block = [], []
            block.append(code_line)
        self.N = len(self.blocks)

    def lex_blocks(self):
        i = 0
        for block in self.blocks:
            self.lexemes.append([])
            for line in block:
                self.lexemes[-1].append(self.lexer(line, i + 1))
                i += 1

    @staticmethod
    def lexer(code_line: str, line_num: int) -> list:
        """
        self.lexemes:
        [
            type:
                0 - variable:
                    name: str,
                    indexes: set[int],
                    is_mutable: bool,
                    phi: bool,
                    comma: bool;
                1 - label:
                    name: str;
                2 - operation:
                    value: str,
                    class: 0 - {param}, 1 - {return}, 2 - {<--}, 3 - {+, -, *, ...},
                    4 - {>, <, =, ...}, 5 - {%div, %mod, ...};
                    comma: bool;
                3 - number:
                    value: int,
                    comma: bool;
                4 - flag:
                    name: str;
                5 - condition:
                    is_true: bool;
                6 - goto:
                    none;
                7 - pass:
                    none.
        ]
        """
        line = []
        for word in code_line.split():
            if not word:
                continue
            lex = word
            if lex[-1] == ',':
                lex = lex[:-1]
            if lex == 'goto':
                line.append([6])
            elif lex == 'ifTrue':
                line.append([5, True])
            elif lex == 'ifFalse':
                line.append([5, False])
            elif lex[-1] == ':' and not line:
                line.append([1, lex[:-1]])
            elif line and line[-1] == [6]:
                line.append([1, lex])
            elif lex[0] == '#' and len(lex) > 1:
                try:
                    line.append([3, int(lex[1:])])
                except Exception as e:
                    raise Exception(f'Bad number. Not recognized word "{lex}" in line {line_num}:\n{str(e)}')
            elif lex[0] == '@' and len(lex) > 1:
                line.append([4, lex[1:]])
            elif lex == 'param':
                line.append([2, lex, 0])
            elif lex == 'return':
                line.append([2, lex, 1])
            elif lex == '<--':
                line.append([2, lex, 2])
            elif lex in ['>', '<', '=', '>=', '<=', '==']:
                line.append([2, lex, 4])
            elif lex[0] == '%' and len(lex) > 1:
                line.append([2, lex[1:], 5])
            elif lex[0] in '*+-' and len(lex) == 1:
                line.append([2, lex, 3])
            elif lex[0].islower():
                line.append([0, lex, [], False, False])
            else:
                raise Exception(f'Not recognized word "{lex}" in line {line_num}.')
            if line[-1][0] in [0, 2, 3]:  # variable, operation, number
                line[-1].append(word[-1] == ',')
            # TODO: is variable - mutable?
        return line

    def graph(self):
        self.edges = [set() for _ in range(self.N)]
        labels = {}
        for i in range(self.N):
            if self.lexemes[i]:
                if self.lexemes[i][0][0][0] == 1:
                    labels[self.lexemes[i][0][0][1]] = i
        for i in range(self.N - 1):
            if self.lexemes[i] and [6] in self.lexemes[i][-1]:
                self.edges[i].add(labels[self.lexemes[i][-1][
                    self.lexemes[i][-1].index([6]) + 1][1]])
            if self.lexemes[i] and [2, 'return', 1] in self.lexemes[i][-1]:
                self.edges[i].add(self.N - 1)
            if not self.lexemes[i] or [5, False] in self.lexemes[i][-1] \
                    or [5, True] in self.lexemes[i][-1] or (
                    [6] not in self.lexemes[i][-1] and [2, 'return', 1] not in self.lexemes[i][-1]):
                self.edges[i].add(i + 1)
