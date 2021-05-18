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
