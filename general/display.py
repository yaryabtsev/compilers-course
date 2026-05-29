import networkx as nx
from networkx.drawing.nx_agraph import to_agraph
import json
import os
import subprocess
import sys
from pathlib import Path

from general.template_assets import ensure_output_assets, render_template


class Display:
    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        ensure_output_assets(Path(self.out_dir).parent)
        regions_dir = os.path.join(self.out_dir, 'regions')
        os.makedirs(regions_dir, exist_ok=True)
        for file_name in os.listdir(regions_dir):
            if file_name.endswith('.png'):
                os.remove(os.path.join(regions_dir, file_name))
        self.orig_stdout = sys.stdout
        self.output = open(os.path.join(out_dir, 'index.html'), 'w')
        sys.stdout = self.output
        self.closed = False
        self.block_name = 'A'
        self.title_id = 0
        self.titles = []
        self.notes = []
        self.n = -1

        print(render_template('report_start.html', asset_prefix='../'))

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def close(self):
        if self.closed:
            return
        if not self.output.closed:
            print(render_template('report_end.html', asset_prefix='../'), file=self.output)
        if sys.stdout is self.output:
            sys.stdout = self.orig_stdout
        self.output.close()
        self.closed = True

    @staticmethod
    def line_count_text(count: int) -> str:
        return f'{count} line' if count == 1 else f'{count} lines'

    @staticmethod
    def draw_graph(nx_graph, path: str, engine: str = 'dot') -> None:
        try:
            graph = to_agraph(nx_graph)
            graph.layout(engine)
            graph.draw(path)
        except ImportError:
            Display.draw_graph_with_graphviz(nx_graph, path, engine)

    @staticmethod
    def draw_graph_with_dot(nx_graph, path: str) -> None:
        Display.draw_graph_with_graphviz(nx_graph, path)

    @staticmethod
    def draw_graph_with_graphviz(nx_graph, path: str, engine: str = 'dot') -> None:
        def quote(value) -> str:
            return json.dumps(str(value))

        graph_attrs = 'rankdir=TB, splines=curved'
        background = 'transparent'
        if engine != 'dot':
            graph_attrs = 'splines=curved, overlap=false, outputorder=edgesfirst'
            background = 'white'

        lines = [
            'digraph G {',
            f'  graph [{graph_attrs}, bgcolor="{background}"];',
            '  node [shape=ellipse, style="filled", fillcolor="white", color="#94a3b8", fontname="Arial"];',
            '  edge [arrowsize=0.6, color="#64748b", fontname="Arial"];',
        ]
        for node in nx_graph.nodes:
            lines.append(f'  {quote(node)};')
        if nx_graph.is_multigraph():
            edges = ((source, target) for source, target, _ in nx_graph.edges(keys=True))
        else:
            edges = nx_graph.edges()
        for source, target in edges:
            lines.append(f'  {quote(source)} -> {quote(target)};')
        lines.append('}')
        subprocess.run([engine, '-Tpng', '-o', path], input='\n'.join(lines),
                       text=True, check=True)

    def show_code(self, lexemes: list, spoilers=None) -> None:
        self.show_title('code-title')
        if spoilers:
            self.show_spoiler(spoilers)
        line = 1
        print('<div class="code-panel">')
        for i in range(len(lexemes)):
            if lexemes[i]:
                print('<article class="mir-block">')
                print('<div class="block-heading">')
                print('<span class="new-block">Block</span> ', end='')
                print(f'<span class="block-name">{self.name(i)}</span> ', end='')
                print(f'<span class="count-lines">{Display.line_count_text(len(lexemes[i]))}</span>')
                print('</div>')

                Display.show_line(lexemes[i], line)
                line += len(lexemes[i])
                print('</article>')
            elif i == 0:
                print('<div class="boundary-block"><span class="block-name">Entry</span></div>')
            elif i == len(lexemes) - 1:
                print('<div class="boundary-block"><span class="block-name">Exit</span></div>')
        print('</div></details>', end='')

    @staticmethod
    def show_line(block: list, line_num: int):
        print(f'<ol class="mir-lines" start="{line_num}">')
        for j in range(len(block)):
            print('<li><span>', end='')
            for k in range(len(block[j])):
                if block[j][k][0] == 0:
                    if block[j][k][4]:
                        print('<phi>&phi;(', end='')
                        if len(block[j][k][2]) > 0:
                            print(', '.join([f'<w{block[j][k][0]}'
                                             f'>{block[j][k][1]}<'
                                             f'/w{block[j][k][0]}'
                                             f'><sub>{idx}</sub>' for idx
                                             in block[j][k][2]]), end='')
                        else:
                            print(f'<w{block[j][k][0]}'
                                  f'><h>*</h>{block[j][k][1]}<'
                                  f'/w{block[j][k][0]}>', end='')
                        print(')</phi>', end='')
                    else:
                        print(f'<w{block[j][k][0]}>'
                              f'{block[j][k][1]}</w'
                              f'{block[j][k][0]}>', end='')
                        if type(block[j][k][2]) is int:
                            print(f'<sup>{block[j][k][2]}'
                                  f'</sup>', end='')
                        elif len(block[j][k][2]) == 1:
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
                          f'&nbsp;'
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

        name = ''.join([word[0] for word in self.titles[self.title_id - 1].lower().split()]).replace('/', '')
        Display.draw_graph(nx_multi_graph, os.path.join(self.out_dir, f'{name}.png'))

        print('<div class="graph-panel">')
        print(f'<img src="{name}.png" alt="{self.titles[self.title_id - 1]}">')
        print('</div></details>')

    def name(self, i: int) -> str:
        if i == -1:
            return 'None'
        if i == 0:
            return 'Entry'
        if i == self.n - 1:
            return 'Exit'
        return self.block_name[:-1] + chr(ord(self.block_name[-1]) + i - 1)

    def show_block_table(self, table: list, columns: list, spoilers=None):
        self.show_title('block-table-title')
        if spoilers:
            self.show_spoiler(spoilers)
        print('<div class="table-scroll"><table>')
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
                    print(f'<td{class_name}>{name}</td>')
                elif type(td) is str:
                    class_name = ' class="none"' if td == 'None' else ''
                    print(f'<td{class_name}>{td}</td>')
                else:
                    try:
                        _td = []
                        nodes = td if type(td) is list else sorted(td)
                        for node in nodes:
                            if type(node) is int:
                                _td.append(self.name(node))
                            else:
                                _td.append(node)
                        print(f'<td>{", ".join(_td)}</td>')
                    except:
                        _td = ""
                        for node in td:
                            if type(node) is list:
                                _td += self.name(node[0])
                            else:
                                _td += node
                        print(f'<td>{_td}</td>')

            print('</tr>')
        print('</tbody>')
        print('</table></div></details>')

    def show_title(self, class_name: str) -> None:
        title = self.titles[self.title_id]
        note = self.notes[self.title_id] if self.title_id < len(self.notes) else ''
        note_html = f'<small class="section-note">{note}</small>' if note else ''
        print(f'<details id="title-{self.title_id}"><summary><h2 class="{class_name}"'
              f'><span class="section-title">{title}</span>{note_html}</h2></summary>')
        self.title_id += 1

    def show_hyperlinks(self):
        links = '\n'.join([Display.href(self.titles[_id], "content", _id) for _id in range(len(self.titles))])
        print(render_template('report_shell.html', links=links, blocks=self.n, sections=len(self.titles)))

    @staticmethod
    def href(title: str, class_name: str, title_id: int):
        return f'<a class="{class_name}" href="#title-{title_id}"><span>{title_id + 1:02d}</span>{title}</a>'

    def show_spoiler(self, html):
        if not html:
            return
        print('<details class="trace"><summary><p class="summary-span">'
              '<span>Trace</span><small class="section-note">derivation steps</small>'
              '</p></summary><div class="trace-code">')
        for item in html:
            if type(item) is list:
                if item[0] == 'tab':
                    print('<br>' + '&nbsp;' * max(0, 4 * item[1] - 1), end='')
                elif item[0] == 'set':
                    print('{', end='')
                    print(',&nbsp;'.join([f'<w0>{var}</w0>' for var in item[1]]), end='')
                    print('}', end='')
                elif item[0] == 'block':
                    print(f'<font class="block-name">{self.name(item[1])}</font>', end='')
                elif item[0] == 'line':
                    self.show_line(item[1], item[2])
                elif item[0] == 'block-set':
                    print('{', end='')
                    print(',&nbsp;'.join([f'<font class="block-name">{self.name(node)}</font>' for node in item[1]]),
                          end='')
                    print('}', end='')
                elif item[0] == 'phi':
                    print(f'<phi>&phi;(<h>*</h><w0>{item[1]}</w0>)</phi>', end='')
                else:
                    print(str(item), end='')
            else:
                print(item, end='')
        print('</div></details>')

    def show_placeholder(self, text: str) -> None:
        self.show_title('placeholder-title')
        print('<div class="placeholder-note">')
        print('<strong>Pending stage</strong>')
        print(f'<p>{text}</p>')
        print('</div></details>')

    def show_phi_table(self, table: list, columns: list, spoilers=None) -> None:
        self.show_block_table(table, columns, spoilers)

    def show_var_table(self, table: list) -> None:
        self.show_title('var-table')
        num_line = 1
        print('<div class="value-grid">')
        for i in range(self.n):
            print('<article class="value-card">')
            print('<div class="block-heading">')
            print('<span class="new-block">Block</span> ', end='')
            print(f'<span class="block-name">{self.name(i)}</span> ', end='')
            print(f'<span class="count-lines">{Display.line_count_text(len(table[i][0]))}</span>')
            print('</div>')
            if len(table[i][0]):
                print('<div class="value-card-body">')
                print('<div class="code compact-code">')
                self.show_line(table[i][0], num_line)
                num_line += len(table[i][0])
                print('</div>')

                print('<div class="table-scroll">')
                self.var_table(table[i][1])
                print('</div>')
                print('</div>')
            else:
                print('<p class="empty-state">No instructions in this block.</p>')
            print('</article>')
        print('</div></details>')

    @staticmethod
    def var_table(table: list) -> None:
        if not table:
            print('<p class="empty-state">No value rows.</p>')
            return
        print('<table class="value-table">')
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
            _vars = []
            for var in table[i][-1]:
                if type(var[0]) is int:
                    _vars.append(f'<w3><h>#</h>{var[0]}</w3>')
                else:
                    _vars.append(f'<w0>{var[0]}</w0><sup>{var[1]}</sup>')
            print(',&nbsp;'.join(_vars))
            print('</td>')
            print('</tr>')
        print('</tbody>')
        print('</table>')

    def show_graphs(self, nx_multi_graphs):
        self.show_title('block-graphs-title')
        print('<div class="region-gallery">')
        for i in range(len(nx_multi_graphs)):
            nx_multi_graphs[i].graph['edge'] = {'arrowsize': '0.6', 'splines': 'curved'}
            nx_multi_graphs[i].graph['graph'] = {'scale': '3'}
            Display.draw_graph(nx_multi_graphs[i], os.path.join(self.out_dir, 'regions', f'{i}.png'),
                               engine='neato')
            print('<figure>')
            print(f'<img src="regions/{i}.png" alt="{self.titles[self.title_id - 1]} step {i + 1}">')
            print(f'<figcaption>Step {i + 1}</figcaption>')
            print('</figure>')
        print('</div></details>')

    def show_control_tree(self, graph):
        self.show_title('block-graphs-title')
        control_tree = []
        for edge in graph:
            if type(edge[1]) is int:
                control_tree.append((edge[0], self.name(edge[1])))
            else:
                control_tree.append(edge)
        nx_control_tree = nx.MultiDiGraph(control_tree)
        nx_control_tree.graph['edge'] = {'arrowsize': '0.6', 'splines': 'curved'}
        nx_control_tree.graph['graph'] = {'scale': '3'}

        name = ''.join([word[0] for word in self.titles[self.title_id - 1].lower().split()]).replace('/', '')
        Display.draw_graph(nx_control_tree, os.path.join(self.out_dir, f'{name}.png'))

        print('<div class="graph-panel">')
        print(f'<img src="{name}.png" alt="{self.titles[self.title_id - 1]}">')
        print('</div></details>')
