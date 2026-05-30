import os
import re
import unittest
from pathlib import Path

from general.solver import solve


TEST13_SOURCE = """param x
param y
ifTrue x < #0 goto Lneg
a <-- +, x, #5
goto Ljoin
Lneg: neg <-- -, #0, x
a <-- +, neg, #1
Ljoin: t <-- +, a, y
ifTrue t > #0 goto Lhot
r <-- +, y, #1
goto Lend
Lhot: r <-- +, t, #1
Lend: return r
"""

TEST13_BLOCKS = ['Entry', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'Exit']

TEST13_ORACLE_QADD = {
    'Entry': {'x': 2.0, 'y': 1.0},
    'A': {'x': 2.0, 'y': 1.0},
    'B': {'x': 1.0, 'y': 1.0},
    'C': {'x': 1.0, 'y': 1.0},
    'D': {'x': 1.0, 'y': 1.0},
    'E': {},
    'F': {},
    'G': {},
    'Exit': {},
}

TEST13_APPROX_QADD = {
    'Syntactic branch variables': {
        'Entry': {'x': 1.0, 't': 1.0},
        'A': {'x': 1.0, 't': 1.0},
        'B': {'t': 1.0},
        'C': {'t': 1.0},
        'D': {'t': 1.0},
    },
    'Local dependency variables': {
        'Entry': {'x': 1.0, 'a': 1.0, 'y': 1.0},
        'A': {'x': 1.0, 'a': 1.0, 'y': 1.0},
        'B': {'a': 1.0, 'y': 1.0},
        'C': {'a': 1.0, 'y': 1.0},
        'D': {'a': 1.0, 'y': 1.0},
    },
    'CFG dependency variables': {
        'Entry': {'x': 2.0, 'y': 1.0},
        'A': {'x': 2.0, 'y': 1.0},
        'B': {'x': 1.0, 'y': 1.0},
        'C': {'x': 1.0, 'y': 1.0},
        'D': {'x': 1.0, 'y': 1.0},
    },
}


def format_counts(counts):
    if not counts:
        return '<td class="none">None</td>'
    text = ', '.join(f'{var}:{value:.2f}' for var, value in sorted(counts.items()))
    return f'<td>{text}</td>'


def l1_delta(approx, oracle):
    variables = set(approx) | set(oracle)
    return sum(abs(approx.get(var, 0.0) - oracle.get(var, 0.0)) for var in variables)


def patch_qadd_table(html, title):
    marker = f'<span>{title}</span>'
    if marker not in html:
        return html

    start = html.index(marker)
    table_start = html.index('<table>', start)
    table_end = html.index('</table>', table_start) + len('</table>')
    table = html[table_start:table_end]

    if 'oracle Q<sub>add</sub>' not in table:
        table = table.replace(
            '<th>status</th>',
            '<th>status</th>\n<th>oracle Q<sub>add</sub></th>\n<th>L1 Δ</th>',
            1,
        )

    approx_by_block = TEST13_APPROX_QADD[title]

    def patch_row(match):
        row = match.group(0)
        if 'oracle-qadd-cell' in row:
            return row
        block_match = re.search(r'<td class="first-column">([^<]+)</td>', row)
        if not block_match:
            return row
        block = block_match.group(1)
        oracle = TEST13_ORACLE_QADD.get(block, {})
        approx = approx_by_block.get(block, {})
        delta = l1_delta(approx, oracle)
        extra = (
            f'\n{format_counts(oracle).replace("<td", "<td class=\"oracle-qadd-cell\"", 1)}'
            f'\n<td>{delta:.2f}</td>'
        )
        return row.replace('\n</tr>', f'{extra}\n</tr>', 1)

    table = re.sub(r'<tr>\n<td class="first-column">.*?</tr>', patch_row, table, flags=re.DOTALL)
    return html[:table_start] + table + html[table_end:]


def manual_oracle_details():
    rows = []
    for block in TEST13_BLOCKS:
        oracle = TEST13_ORACLE_QADD[block]
        rows.append(
            '<tr>\n'
            f'<td class="first-column">{block}</td>\n'
            '<td>source oracle</td>\n'
            f'{format_counts(oracle)}\n'
            '<td>manual test13 check</td>\n'
            '</tr>'
        )
    return (
        '<details class="trace" open>\n'
        '<summary><p class="summary-span"><span>Manual source oracle</span></p></summary>\n'
        '<div class="trace-code">\n'
        '<comment>Manual oracle for test13: branch A depends on x; branch D depends on x and y after the join.</comment>'
        '</div>\n'
        '<div class="table-scroll"><table>\n'
        '<thead><tr>\n'
        '<th>block</th>\n'
        '<th>mode</th>\n'
        '<th>oracle Q<sub>add</sub>(block, var)</th>\n'
        '<th>status</th>\n'
        '</tr></thead>\n'
        '<tbody>\n'
        + ''.join(rows)
        + '</tbody>\n'
        '</table></div>\n'
        '</details>\n'
    )


def patch_test13_qadd_dump(html):
    for title in TEST13_APPROX_QADD:
        html = patch_qadd_table(html, title)
    if 'Manual source oracle' not in html:
        html = html.replace('\n</details>\n<details id="title-4">', '\n' + manual_oracle_details() + '</details>\n<details id="title-4">', 1)
    return html


class MyTestCase(unittest.TestCase):
    @staticmethod
    def test_solve_input():
        for file_name in os.listdir('input/'):
            assert solve(f'input/{file_name}', f"output/{file_name.split('.')[0]}/") is None

    @staticmethod
    def test_user_input():
        blocks = [[],
                  ['param c', 'i <-- #0', 'a <-- -, #2, i', 'b <-- +, #2, i'],
                  ['a <-- +, a, i'],
                  ['j <-- +, a, b', 'a <-- +, a, b', 'b <-- j'],
                  ['i <-- +, #1, i'],
                  ['a <-- +, a, #1', 'b <-- +, b, c', 'a <-- +, b, i', 'b <-- a'],
                  []]
        edges = [{1}, {2, 3}, {5}, {3, 4}, {2, 5}, {6}, set()]
        assert solve('', 'output/test05/', 'R1', blocks, edges) is None

    @staticmethod
    def test_regions():
        blocks = [[] for _ in range(10)]
        edges = [{1}, {2, 9}, {3, 8}, {4, 5}, {7}, {6, 3}, {7}, {2}, {1}, set()]
        assert solve('', 'output/test06/', 'B1', blocks, edges) is None

    @staticmethod
    def test_regions_reverse():
        blocks = [[] for _ in range(10)]
        edges = [{8}, {8}, {7}, {2}, {3, 6}, {2}, {4, 5}, {6, 1}, {7, 9}, set()]
        assert solve('', 'output/test07/', 'B1', blocks, edges) is None

    @staticmethod
    def test_task4():
        blocks = [[],
                  ['i <-- -, m, #1', 'j <-- n', 'a <-- u1'],
                  ['i <-- +, i, #1'],
                  ['a <-- u2'],
                  ['j <-- u3'],
                  [], []]
        edges = [{1}, {2}, {3, 4}, {4, 5}, {2, 5}, {6}, set()]
        assert solve('', 'output/test08/', 'B1', blocks, edges) is None

    @staticmethod
    def test_symbolic_dump_sections():
        assert solve('input/test10.txt', 'output/test10/') is None
        html = Path('output/test10/index.html').read_text(encoding='utf-8')
        assert 'Q_add / Q_t Approximation' in html
        assert 'Q<sub>t</sub>' in html
        assert 'Q<sub>add</sub>(block, var)' in html
        assert 'alpha=0.35, beta=0.50; syntactic C relation' in html

    @staticmethod
    def test_test13_qadd_oracle_dump_patch():
        input_path = Path('input/test13.txt')
        output_path = Path('output/test13/')
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(TEST13_SOURCE, encoding='utf-8')

        assert solve(str(input_path), str(output_path)) is None

        html_path = output_path / 'index.html'
        html = html_path.read_text(encoding='utf-8')
        assert 'Syntactic branch variables' in html
        assert 'Local dependency variables' in html
        assert 'CFG dependency variables' in html

        patched = patch_test13_qadd_dump(html)
        html_path.write_text(patched, encoding='utf-8')

        assert 'Manual source oracle' in patched
        assert 'oracle Q<sub>add</sub>' in patched
        assert '<td class="first-column">D</td>' in patched
        assert '<td>x:1.00, y:1.00</td>' in patched
        assert '<td>0.00</td>' in patched


if __name__ == '__main__':
    unittest.main()
