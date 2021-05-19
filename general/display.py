import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
import os
import sys


class Display:
    def __init__(self, out_dir: str):
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        self.out_dir = out_dir
        self.orig_stdout = sys.stdout
        self.output = open(os.path.join(out_dir, 'index.html'), 'w')
        sys.stdout = self.output
        self.block_name = 'A'
        self.title_id = 0
        self.titles = []
        self.n = -1

        print('<!DOCTYPE html><html lang="en"><head><link rel="icon"'
              ' type="image/png" sizes="32x32" href="../coding.png">'
              '<link rel="stylesheet" href="../styles.css"><title>So'
              'me Code</title></head><body>')

    def __del__(self):
        print('<footer></footer></body></html>')
        sys.stdout = self.orig_stdout
        self.output.close()

    def show_code(self, lexemes: list, spoilers: list = []) -> None:
        self.show_title('code-title')
        if spoilers:
            self.show_spoiler(spoilers)
        line = 1
        print('<div class="wrapper"><div class="code">')
        for i in range(len(lexemes)):
            if lexemes[i]:
                print(f'<font class="new-block">Block</font> ', end='')
                print(f'<font class="block-name">{self.name(i)}', end='')
                print(f'</font> <font class="count-lines">[{len(lexemes[i])}]</font>')

                Display.show_line(lexemes[i], line)
                line += len(lexemes[i])
            elif i == 0:
                print(f'<div class="block-name">Entry</div>')
            elif i == len(lexemes) - 1:
                print(f'<div class="block-name">Exit</div>')
        print('</div></div>', end='')

    @staticmethod
    def show_line(block: list, line_num: int):
        print(f'<ol start="{line_num}">')
        for j in range(len(block)):
            print('<li><span>', end='')
            for k in range(len(block[j])):
                if block[j][k][0] == 0:
                    if block[j][k][4]:
                        print('<phi>&phi;(', end='')
                        print(', '.join([f'<w{block[j][k][0]}'
                                         f'>{block[j][k][1]}<'
                                         f'/w{block[j][k][0]}'
                                         f'><sub>{idx}</sub>' for idx
                                         in block[j][k][2]]), end='')
                        print(')</phi>', end='')
                    else:
                        print(f'<w{block[j][k][0]}>'
                              f'{block[j][k][1]}</w'
                              f'{block[j][k][0]}>', end='')
                        if len(block[j][k][2]) == 1:
                            print(f'<sup>{block[j][k][2][0]}'
                                  f'</sup>', end='')
                        elif len(block[j][k][2]) > 1:
                            raise Exception(f'Too many indexes for not phi '
                                            f'variable: {block[j][k]}.')
                elif block[j][k][0] == 1:
                    print(f'<w{block[j][k][0]}>'
                          f'{block[j][k][1]}</w'
                          f'{block[j][k][0]}>', end='')
                    if k == 0:
                        print(':', end='')
                elif block[j][k][0] == 2:
                    print(f'<w{block[j][k][0]}'
                          f'{block[j][k][2]}>', end='')
                    special_character = {'<--': '&xlarr;', '<=': '&le;',
                                         '>=': '&ge;', '==': '&equiv;'}
                    if block[j][k][1] in special_character.keys():
                        print(special_character[block[j][k][1]], end='')
                    elif block[j][k][2] == 5:
                        print(f'<h>%</h>{block[j][k][1]}', end='')
                    else:
                        print(f'{block[j][k][1]}', end='')
                    print(f'</w{block[j][k][0]}'
                          f'{block[j][k][2]}>', end='')
                elif block[j][k][0] == 3:
                    print(f'<w{block[j][k][0]}>'
                          f'<h>#</h>{block[j][k][1]}</'
                          f'w{block[j][k][0]}>', end='')
                elif block[j][k][0] == 4:
                    print(f'<w{block[j][k][0]}>'
                          f'<h>@</h>{block[j][k][1]}</'
                          f'w{block[j][k][0]}>', end='')
                elif block[j][k][0] == 5:
                    print(f'<if>if</if>'
                          f'<w{block[j][k][0]}>'
                          f'{block[j][k][1]}<'
                          f'/w{block[j][k][0]}>', end='')
                elif block[j][k][0] == 6:
                    print(f'<w{block[j][k][0]}>'
                          f'goto</w{block[j][k][0]}>', end='')
                elif block[j][k][0] == 7:
                    print(f'<w{block[j][k][0]}>'
                          f'pass</w{block[j][k][0]}>', end='')
                if block[j][k][0] in [0, 2, 3] and block[j][k][-1]:
                    print(',', end='')
                print('&nbsp;', end='')
            print('</span></li>')
        print('</ol>')

    def show_graph(self, edges: list):
        self.show_title('image-title')
        multi_graph = []
        for i in range(len(edges)):
            for node in edges[i]:
                multi_graph.append((self.name(i), self.name(node)))

        nx_multi_graph = nx.MultiDiGraph(multi_graph)
        nx_multi_graph.graph['edge'] = {'arrowsize': '0.6', 'splines': 'curved'}
        nx_multi_graph.graph['graph'] = {'scale': '3'}

        graph = to_agraph(nx_multi_graph)
        graph.layout('dot')

        name = ''.join([word[0] for word in self.titles[self.title_id - 1].lower().split()]).replace('/', '')
        graph.draw(f'{self.out_dir}/{name}.png')

        print(f'<img src="{name}.png" alt="{self.titles[self.title_id - 1]}">')

    def name(self, i: int) -> str:
        if i == -1:
            return 'None'
        if i == 0:
            return 'Entry'
        if i == self.n - 1:
            return 'Exit'
        return self.block_name[:-1] + chr(ord(self.block_name[-1]) + i - 1)

    def show_block_table(self, table: list, columns: list, spoilers: list = []):
        self.show_title('block-table-title')
        if spoilers:
            self.show_spoiler(spoilers)
        print('<table>')
        print('<thead><tr>')
        print(f'<th>{columns[0]}</th>')
        for column in columns[1:]:
            if type(column) is int:
                print(f'<th>{self.name(column)}</th>')
            else:
                print(f'<th>{column}</th>')
        print('</tr></thead>')
        print('<tbody>')
        for row in table:
            print('<tr>')
            print(f'<td class="first-column">{row[0]}</td>')
            for td in row[1:]:
                if type(td) is bool:
                    if td:
                        print(f'<td class="true">+</td>')
                    else:
                        print(f'<td class="false">-</td>')
                elif not td and td != 0:
                    print(f'<td class="none">None</td>')
                elif type(td) is int:
                    name = self.name(td)
                    class_name = ''
                    if name == 'None':
                        class_name = ' class="none"'
                    print(f'<td {class_name}>{name}</td>')
                else:
                    print(f'<td>{", ".join([self.name(node) for node in sorted(td)])}</td>')
            print('</tr>')
        print('</tbody>')
        print('</table>')

    def show_title(self, class_name: str) -> None:
        print(f'<h2 class="{class_name}" id="title-{self.title_id}">{self.titles[self.title_id]}</h2>')
        self.title_id += 1

    def show_hyperlinks(self):
        print(f'<header>')
        for id in range(len(self.titles)):
            Display.show_href(self.titles[id], "content", id)
        print(f'</header>')

    @staticmethod
    def show_href(title: str, class_name: str, title_id: int):
        print(f'<a class="{class_name}" href="#title-{title_id}">{title}</a>')

    def show_spoiler(self, html):
        if not html:
            return
        print('<div class="spoilers"><div class="code">')
        for item in html:
            if type(item) is list:
                if item[0] == 'tab':
                    print('<br>' + '&nbsp' * (4 * item[1] - 1), end='')
                elif item[0] == 'set':
                    print('{', end='')
                    print(',&nbsp'.join([f'<w0>{var}</w0>' for var in item[1]]), end='')
                    print('}', end='')
                elif item[0] == 'block':
                    print(f'<font class="block-name">{self.name(item[1])}</font>')
                elif item[0] == 'line':
                    self.show_line(item[1], item[2])
                elif item[0] == 'block-set':
                    print('{', end='')
                    print(',&nbsp'.join([f'<font class="block-name">{self.name(node)}</font>' for node in item[1]]),
                          end='')
                    print('}', end='')
                elif item[0] == 'phi':
                    print(f'<phi>&phi;(<h>*</h><w0>{item[1]}</w0>)</phi>', end='')
                else:
                    print(str(item))
            else:
                print(item, end='')
        print('</div></div>')

    def show_phi_table(self, param):
        pass

    def show_var_table(self, table: list) -> None:
        self.show_title('var-table')
        num_line = 1
        print('<table>')
        print('<tbody>')
        for i in range(self.n):
            print('<tr>')
            print(f'<td colspan="2"><font class="new-block">Block</font> ', end='')
            print(f'<font class="block-name">{self.name(i)}', end='')
            print(f'</font> <font class="count-lines">[{len(table[i][0])}]</font></td>')
            print('</tr>')

            if len(table[i][0]):
                print('<tr>')
                print('<td><div class="wrapper"><div class="code">')
                self.show_line(table[i][0], num_line)
                num_line += len(table[i][0])
                print('</div></div></td>')

                print('<td>')
                self.var_table(table[i][1])
                print('</td>')
                print('</tr>')
        print('</tbody>')
        print('</table>')

    def var_table(self, table: list) -> None:
        if not table:
            return
        print('<table>')
        print('<tbody>')
        columns = len(max(table, key=lambda x: len(x)))
        for i in range(len(table)):
            print('<tr>')
            print(f'<td>{i + 1}</td>')
            if table[i][0] == 'id/nm':
                print(f'<td><nm>{table[i][0]}</nm></td>')
            elif len(table[i][0]) == 1:
                print(f'<td><w23>{table[i][0]}</w23></td>')
            else:
                print(f'<td><w25><h>%</h>{table[i][0]}</w25></td>')
            for j in range(1, len(table[i]) - 1):
                print(f'<td><num>{table[i][j]}</num></td>')
            if columns - len(table[i]) > 0:
                print(f'<td colspan="{columns - len(table[i])}"></td>')
            print('<td>')
            vars = []
            for var in table[i][-1]:
                if type(var[0]) is int:
                    vars.append(f'<w3><h>#</h>{var[0]}</w3>')
                else:
                    vars.append(f'<w0>{var[0]}</w0><sup>{var[1]}</sup>')
            print(',&nbsp'.join(vars))
            print('</td>')
            print('</tr>')
        print('</tbody>')
        print('</table>')
