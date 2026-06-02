from typing import List


class Dominator:
    def __init__(self, edges):
        self.N = len(edges)
        self.edges = edges
        self.available = Dominator.dfs(self.edges, 0)

        self.dom_list = [{0, node} for node in range(self.N)]
        self.calc_dom()

        self.idom_list = [-1] * self.N
        self.calc_idom()

        self.pred_list = [set() for _ in range(self.N)]
        self.calc_pred()

        self.df_list = [set() for _ in range(self.N)]
        self.calc_df()

        self.dom_edges = [set() for _ in range(self.N)]
        self.dom_tree()

    @staticmethod
    def dfs(edges: list, start: int, visited: list = None) -> List[bool]:
        if visited is None:
            visited = [False] * len(edges)
        visited[start] = True
        for next_node in edges[start]:
            if not visited[next_node]:
                Dominator.dfs(edges, next_node, visited)
        return visited

    def calc_dom(self) -> None:
        for taboo in range(1, self.N):
            if self.available[taboo]:
                accessible = Dominator.dfs(
                    self.edges, 0, [taboo == node for node in range(self.N)])
                for i in range(self.N):
                    if not accessible[i]:
                        self.dom_list[i].add(taboo)

    def calc_idom(self) -> None:
        for node1 in range(self.N):
            if self.available[node1]:
                for dom_node1 in self.dom_list[node1]:
                    flag = (dom_node1 != node1)
                    node2 = 0
                    while node2 < self.N and flag:
                        if self.available[node1]:
                            if node2 != dom_node1 and node2 != node1:
                                if dom_node1 in self.dom_list[node2]:
                                    if node2 in self.dom_list[node1]:
                                        flag = False
                        node2 += 1
                    if flag:
                        self.idom_list[node1] = dom_node1

    def calc_pred(self) -> None:
        for node1 in range(self.N):
            if self.available[node1]:
                for node2 in self.edges[node1]:
                    self.pred_list[node2].add(node1)

    def calc_df(self):
        for node in range(self.N):
            if self.available[node] and len(self.pred_list[node]) > 1:
                for pred in self.pred_list[node]:
                    curr_pred: int = pred
                    while curr_pred is not None and curr_pred != self.idom_list[node]:
                        self.df_list[curr_pred].add(node)
                        if self.idom_list[curr_pred] != -1:
                            curr_pred = self.idom_list[curr_pred]

    def dom_tree(self):
        for node in range(self.N):
            if self.idom_list[node] is not None:
                if self.idom_list[node] != -1:
                    self.dom_edges[self.idom_list[node]].add(node)

    def get_table(self):
        columns = ["node ="]
        for node in range(self.N):
            if self.available[node]:
                columns.append(node)
        table = []
        fields = vars(self)
        for key in ['Pred', 'Dom', 'Idom', 'DF']:
            row = [key + '(node)']
            for i in range(self.N):
                if self.available[i]:
                    row.append(fields[key.lower() + '_list'][i])
            table.append(row)
        return table, columns


class PostDominator:
    def __init__(self, edges):
        self.N = len(edges)
        self.edges = edges
        self.reverse_edges = [set() for _ in range(self.N)]
        self.calc_reverse_edges()
        self.available = Dominator.dfs(self.reverse_edges, self.N - 1)

        self.pdom_list = [set() for _ in range(self.N)]
        self.calc_pdom()

        self.ipdom_list = [-1] * self.N
        self.calc_ipdom()

        self.cd_list = [set() for _ in range(self.N)]
        self.calc_control_dependence()

    def calc_reverse_edges(self) -> None:
        for node in range(self.N):
            for child in self.edges[node]:
                self.reverse_edges[child].add(node)

    def calc_pdom(self) -> None:
        nodes = {node for node in range(self.N) if self.available[node]}
        for node in nodes:
            self.pdom_list[node] = set(nodes)
        self.pdom_list[self.N - 1] = {self.N - 1}
        changed = True
        while changed:
            changed = False
            for node in range(self.N - 2, -1, -1):
                if not self.available[node]:
                    continue
                successors = [child for child in self.edges[node] if self.available[child]]
                if successors:
                    common = set(self.pdom_list[successors[0]])
                    for child in successors[1:]:
                        common &= self.pdom_list[child]
                else:
                    common = set()
                new_pdom = {node} | common
                if new_pdom != self.pdom_list[node]:
                    self.pdom_list[node] = new_pdom
                    changed = True

    def calc_ipdom(self) -> None:
        for node in range(self.N):
            strict_pdom = self.pdom_list[node] - {node}
            if strict_pdom:
                self.ipdom_list[node] = max(strict_pdom, key=lambda child: len(self.pdom_list[child]))

    def calc_control_dependence(self) -> None:
        for node in range(self.N):
            if not self.available[node]:
                continue
            for child in self.edges[node]:
                if not self.available[child]:
                    continue
                runner = child
                while runner != -1 and runner != self.ipdom_list[node]:
                    self.cd_list[runner].add(node)
                    runner = self.ipdom_list[runner]

    def get_table(self):
        columns = ["node ="]
        for node in range(self.N):
            if self.available[node]:
                columns.append(node)
        table = []
        fields = vars(self)
        for key in ['Pdom', 'Ipdom', 'CD']:
            row = [key + '(node)']
            for i in range(self.N):
                if self.available[i]:
                    row.append(fields[key.lower() + '_list'][i])
            table.append(row)
        return table, columns
