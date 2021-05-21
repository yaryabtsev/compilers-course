import networkx as nx


class Regions:
    def __init__(self, dominator, code_blocks):
        self.gen = [set() for _ in range(dominator.N)]
        self.kill = [set() for _ in range(dominator.N)]
        self.code_blocks = code_blocks
        self.instructions = []
        self.parse_instructions()
        self.classification = [['Re'], [], []]
        self.dominator = dominator
        self.multi_graph = [set() for _ in range(dominator.N)]
        # self.reverse_graph = [set() for _ in range(dominator.N)]
        self.nodes = [-2] * dominator.N
        self.keys = [-2] * dominator.N
        self.N = dominator.N
        self.control_tree = []
        self.rename()

    def find_regions(self):
        yield self.graph_object()
        while True:
            multi_graph = []
            for i in range(self.N):
                for node in self.multi_graph[i]:
                    if node != -2:
                        multi_graph.append((i, node))
            nx_multi_graph = nx.MultiDiGraph(multi_graph)
            loops = sorted(nx.simple_cycles(nx_multi_graph), key=lambda x: len(x))
            loops = sorted(loops, key=lambda x: x[0], reverse=True)
            if not loops:
                for i in range(self.N):
                    if self.multi_graph[i]:
                        self.control_tree.append((f'R{self.N - 1}', f'R{i}'))
                    elif i == self.N - 1:
                        self.control_tree.append((f'R{self.N - 1}', 'Re'))
                self.classification[1].append(f'R{self.N - 1}')
                # print(sorted(self.control_tree))
                return
            self.replace_loop(loops[0])
            yield self.graph_object()

    def graph_object(self):
        multi_graph = []
        for i in range(self.N):
            for node in self.multi_graph[i]:
                if node == -1:
                    multi_graph.append((f'R{i}', 'Re'))
                else:
                    multi_graph.append((f'R{i}', f'R{node}'))
        return nx.MultiDiGraph(multi_graph)

    def rename(self):
        n = 0
        self.nodes[n] = 0
        self.keys[0] = n
        n += 1
        i = 0
        while i < n:
            for child in self.dominator.edges[self.nodes[i]]:
                if child != self.dominator.N - 1 and self.keys[child] == -2:
                    self.nodes[n] = child
                    self.keys[child] = n
                    n += 1
            i += 1
        self.nodes[n] = -1
        self.keys[-1] = -1
        for i in range(self.dominator.N):
            if self.keys[i] != -2:
                for node in self.dominator.edges[i]:
                    self.multi_graph[self.keys[i]].add(self.keys[node])
        for i in range(self.dominator.N):
            if i == self.dominator.N - 1:
                self.control_tree.append(('Re', 'Exit'))
            elif self.nodes[i] != -2:
                self.classification[0].append(f'R{i}')
                self.control_tree.append((f'R{i}', self.nodes[i]))

    def replace_loop(self, loop):
        self.multi_graph.append(set())
        if len(loop) != 1:
            self.classification[1].append(f'R{self.N - 1}')
            self.multi_graph[self.N - 1].add(self.N - 1)
        else:
            self.classification[2].append(f'R{self.N - 1}')
        reverse_graph = self.reverse()
        i = 1
        n = len(loop)
        while i < n:
            for node in reverse_graph[loop[i]]:
                if node not in loop:
                    loop.append(node)
                    n += 1
            i += 1
        for node in loop:
            self.control_tree.append((f'R{self.N - 1}', f'R{node}'))
        for n in loop:
            for node in self.multi_graph[n]:
                if node not in loop:
                    self.multi_graph[self.N - 1].add(node)
        for node in reverse_graph[loop[0]]:
            self.multi_graph[node].add(self.N - 1)
            self.multi_graph[node] -= {loop[0]}
        for node in loop:
            self.multi_graph[node] = set()
        self.N += 1

    def reverse(self):
        graph = [set() for _ in range(len(self.multi_graph))]
        for i in range(len(self.multi_graph)):
            for node in self.multi_graph[i]:
                graph[node].add(i)
        return graph

    def gen_kill(self):
        columns = ['block'] + [i for i in range(self.dominator.N)]
        table = [['gen<sub>block</sub>'] + [{f'd<sub>{i + 1}</sub>' for i in block} for block in self.gen],
                 ['kill<sub>block</sub>'] + [{f'd<sub>{i + 1}</sub>' for i in block} for block in self.kill]]
        return table, columns, [
            '<comment>The instruction index corresponds to the line number in the original code.</comment>']

    def parse_instructions(self):
        i = 0
        j = 0
        for block in self.code_blocks:
            for line in block:
                self.instructions.append([])
                for word in line:
                    if word[0] == 0 and word[3]:
                        # and [j, word[1]] not in self.instructions:  # for unique instructions
                        self.instructions[i] = [j, word[1]]
                        self.gen[j].add(i)
                i += 1
            j += 1
        n = len(self.instructions)
        for i in range(n):
            if self.instructions[i]:
                for j in range(i + 1, n):
                    if self.instructions[j]:
                        if self.instructions[i][0] != self.instructions[j][0] and self.instructions[i][1] == \
                                self.instructions[j][1]:
                            self.kill[self.instructions[i][0]].add(j)
                            self.kill[self.instructions[j][0]].add(i)

    def transfer_function(self):
        spoilers = []
        table = []
        i = 0
        while self.control_tree[i][0] != 'Re':
            i += 1
        i += 1
        while i < len(self.control_tree):
            row = [self.control_tree[i][0]]
            tf = '<div class="code">'
            j = i
            while j < len(self.control_tree) and self.control_tree[i][0] == self.control_tree[j][0]:
                tf += f'f<sub>{self.control_tree[i][0]}, In[{self.control_tree[j][1]}]</sub> = '
                lst = []
                for pred in self.preds(self.control_tree[j][1]):
                    lst.append(f'f<sub>{self.control_tree[i][0]}, Out[{pred}]</sub>')
                tf += ' &and; '.join(lst)
                tf += '<br>'
                h = self.find(self.control_tree[j][1])
                while h < len(self.control_tree) and self.control_tree[h][0] == self.control_tree[j][1]:
                    tf += f'f<sub>{self.control_tree[i][0]}, Out[{self.control_tree[h][1]}]</sub> = '
                    tf += f'f<sub>{self.control_tree[j][1]}, Out[{self.control_tree[h][1]}]</sub> &#176; '
                    tf += f'f<sub>{self.control_tree[i][0]}, In[{self.control_tree[j][1]}]</sub>  '
                    h += 1
                tf += '<br>'
                j += 1
            row.append([tf + '</div'])
            gen = '<div class="code">'

            row.append([gen + '</div'])
            kill = '<div class="code">'

            row.append([kill + '</div'])
            table.append(row)
            i += 1
        return table, ['region', 'Transfer Function', 'gen', 'kill'], []

    def preds(self, name):
        if name == 'Exit':
            return self.dominator.pred_list[-1]
        if name == 'Entry':
            return self.dominator.pred_list[0]
        if type(name) is int:
            return self.dominator.pred_list[name]
        for edge in self.control_tree:
            if edge[0] == name:
                return self.preds(edge[1])
        return []

    def find(self, name):
        i = 0
        for edge in self.control_tree:
            if edge[0] == name:
                return i
            i += 1
        return 0
