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
        print('<!DOCTYPE html><html lang="en"><head><link rel="icon"'
              ' type="image/png" sizes="32x32" href="../coding.png"><'
              'link rel="stylesheet" href="../styles.css"><title>Som'
              'e Code</title></head><body>')

    def __del__(self):
        print('<footer></footer></body></html>')
        sys.stdout = self.orig_stdout
        self.output.close()

    @staticmethod
    def show_code(lexemes: list, title: str, title_id: int, block_name: str = 'A') -> None:
        Display.show_title(title, 'code-title', title_id)
        line = 1
        print('<div class="wrapper"><div class="code">')
        for i in range(len(lexemes)):
            if lexemes[i]:
                print(f'<font class="new-block">Block</font> ', end='')
                print(f'<font class="block-name">{block_name}', end='')
                print(f'</font> <font class="count-lines">[{len(lexemes[i])}]</font>')
                block_name = block_name[:-1] + chr(ord(block_name[-1]) + 1)
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
                        if not block[j][k][2]:
                            print(f'<w{block[j][k][0]}>'
                                  f'{block[j][k][1]}</w'
                                  f'{block[j][k][0]}>', end='')
                        if len(block[j][k][2]) == 1:
                            print(f'<sub>{block[j][k][2][0]}'
                                  f'</sub>', end='')
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
                if block[j][k][0] in [0, 2, 3] and block[j][k][-1]:
                    print(',', end='')
                print('&nbsp;', end='')
            print('</span></li>')
        print('</ol>')

    def show_graph(self, edges: list, title: str, title_id: int, block_name: str = 'A'):
        multi_graph = []
        for i in range(len(edges)):
            for node in edges[i]:
                multi_graph.append((Display.name(i, len(edges), block_name),
                                    Display.name(node, len(edges), block_name)))

        nx_multi_graph = nx.MultiDiGraph(multi_graph)
        nx_multi_graph.graph['edge'] = {'arrowsize': '0.6', 'splines': 'curved'}
        nx_multi_graph.graph['graph'] = {'scale': '3'}

        graph = to_agraph(nx_multi_graph)
        graph.layout('dot')

        name = ''.join([word[0] for word in title.lower().split()])
        graph.draw(f'{self.out_dir}/{name}.png')

        Display.show_title(title, 'image-title', title_id)
        print(f'<img src="{name}.png" width="189" height="255" alt="{title}">')

    @staticmethod
    def name(i: int, n: int, block_name: str = 'A') -> str:
        if i == -1:
            return 'None'
        if i == 0:
            return 'Entry'
        if i == n - 1:
            return 'Exit'
        return block_name[:-1] + chr(ord(block_name[-1]) + i - 1)

    @staticmethod
    def show_block_table(table: list, columns: list, n: int, title: str, title_id: int, block_name: str = 'A'):
        Display.show_title(title, 'block-table-title', title_id)
        print('<table>')
        print('<thead><tr>')
        print(f'<th>{columns[0]}</th>')
        for column in columns[1:]:
            print(f'<th>{Display.name(column, n, block_name)}</th>')
        print('</tr></thead>')
        print('<thead>')
        for row in table:
            print('<tr>')
            print(f'<td class="first-column">{row[0]}</td>')
            for td in row[1:]:
                if not td and td != 0:
                    print(f'<td class="none">None</td>')
                elif type(td) is int:
                    print(f'<td>{Display.name(td, n, block_name)}</td>')
                else:
                    print(f'<td>{", ".join([Display.name(node, n, block_name) for node in sorted(td)])}</td>')
            print('</tr>')
        print('</thead>')
        print('</table>')

    @staticmethod
    def show_title(title: str, class_name: str, title_id: int) -> None:
        print(f'<h1 class="{class_name}" id="title-{title_id}">{title}</h1>')

    @staticmethod
    def show_hyperlinks(titles):
        print(f'<header>')
        for id in range(len(titles)):
            Display.show_href(titles[id], "content", id)
        print(f'</header>')

    @staticmethod
    def show_href(title: str, class_name: str, title_id: int):
        print(f'<a class="{class_name}" href="#title-{title_id}">{title}</a>')

