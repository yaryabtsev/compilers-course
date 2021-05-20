import networkx as nx


class Regions:
    def __init__(self, dominator):
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
            if i == 0:
                self.control_tree.append(('R0', 'Entry'))
            elif i == self.dominator.N - 1:
                self.control_tree.append(('Re', 'Exit'))
            elif self.nodes[i] != -2:
                self.control_tree.append((f'R{i}', self.nodes[i]))

    def replace_loop(self, loop):
        self.multi_graph.append(set())
        if len(loop) != 1:
            self.multi_graph[self.N - 1].add(self.N - 1)
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
