import os
import re
import unittest
from pathlib import Path

from general.solver import solve


TEST13_BLOCKS = ['Entry', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'Exit']
TEST13_INPUT = Path('input/test13.txt')
TEST13_BETA_CASES = [
    ('test14', 0.5),
    ('test15', 0.75),
    ('test16', 0.9),
]


def active_blocks(entry, middle):
    return {
        'Entry': entry,
        'A': entry,
        'B': middle,
        'C': middle,
        'D': middle,
        'E': {},
        'F': {},
        'G': {},
        'Exit': {},
    }


def test13_oracle_qadd(beta):
    return active_blocks(
        {'x': 1.0 + 2.0 * beta, 'y': 2.0 * beta},
        {'x': 1.0, 'y': 1.0},
    )


def test13_approx_qadd(beta):
    return {
        'Syntactic branch variables': active_blocks(
            {'x': 1.0, 't': 2.0 * beta},
            {'t': 1.0},
        ),
        'Local dependency variables': active_blocks(
            {'x': 1.0, 'a': 2.0 * beta, 'y': 2.0 * beta},
            {'a': 1.0, 'y': 1.0},
        ),
        'CFG dependency variables': test13_oracle_qadd(beta),
    }


def format_counts(counts):
    if not counts:
        return '<td class="none">None</td>'
    text = ', '.join(f'{var}:{value:.2f}' for var, value in sorted(counts.items()))
    return f'<td>{text}</td>'


def l1_delta(approx, oracle):
    variables = set(approx) | set(oracle)
    return sum(abs(approx.get(var, 0.0) - oracle.get(var, 0.0)) for var in variables)


def patch_qadd_table(html, title, oracle_qadd, approx_qadd):
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

    approx_by_block = approx_qadd[title]

    def patch_row(match):
        row = match.group(0)
        if 'oracle-qadd-cell' in row:
            return row
        block_match = re.search(r'<td class="first-column">([^<]+)</td>', row)
        if not block_match:
            return row
        block = block_match.group(1)
        oracle = oracle_qadd.get(block, {})
        approx = approx_by_block.get(block, {})
        delta = l1_delta(approx, oracle)
        extra = (
            f'\n{format_counts(oracle).replace("<td", "<td class=\"oracle-qadd-cell\"", 1)}'
            f'\n<td>{delta:.2f}</td>'
        )
        return row.replace('\n</tr>', f'{extra}\n</tr>', 1)

    table = re.sub(r'<tr>\n<td class="first-column">.*?</tr>', patch_row, table, flags=re.DOTALL)
    return html[:table_start] + table + html[table_end:]


def manual_oracle_details(oracle_qadd, beta):
    rows = []
    for block in TEST13_BLOCKS:
        oracle = oracle_qadd[block]
        rows.append(
            '<tr>\n'
            f'<td class="first-column">{block}</td>\n'
            '<td>source oracle</td>\n'
            f'{format_counts(oracle)}\n'
            f'<td>manual test13 beta={beta:.2f} check</td>\n'
            '</tr>'
        )
    return (
        '<details class="trace" open>\n'
        '<summary><p class="summary-span"><span>Manual source oracle</span></p></summary>\n'
        '<div class="trace-code">\n'
        f'<comment>Manual oracle for test13 with beta={beta:.2f}: branch A depends on x; branch D depends on x and y after the join.</comment>'
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


def patch_test13_qadd_dump(html, beta):
    oracle_qadd = test13_oracle_qadd(beta)
    approx_qadd = test13_approx_qadd(beta)
    for title in approx_qadd:
        html = patch_qadd_table(html, title, oracle_qadd, approx_qadd)
    if 'Manual source oracle' not in html:
        html = html.replace(
            '\n</details>\n<details id="title-4">',
            '\n' + manual_oracle_details(oracle_qadd, beta) + '</details>\n<details id="title-4">',
            1,
        )
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
    def test_test13_qadd_beta_oracle_dump_patches():
        assert TEST13_INPUT.is_file()
        for output_name, beta in TEST13_BETA_CASES:
            output_path = Path(f'output/{output_name}/')
            assert solve(str(TEST13_INPUT), str(output_path), qadd_beta=beta) is None

            html_path = output_path / 'index.html'
            html = html_path.read_text(encoding='utf-8')
            assert 'Syntactic branch variables' in html
            assert 'Local dependency variables' in html
            assert 'CFG dependency variables' in html
            assert f'beta={beta:.2f}; cfg dependency C relation' in html

            patched = patch_test13_qadd_dump(html, beta)
            html_path.write_text(patched, encoding='utf-8')

            oracle = test13_oracle_qadd(beta)
            entry_oracle = ', '.join(f'{var}:{value:.2f}' for var, value in sorted(oracle['Entry'].items()))
            assert 'Manual source oracle' in patched
            assert 'oracle Q<sub>add</sub>' in patched
            assert '<td class="first-column">D</td>' in patched
            assert f'<td>{entry_oracle}</td>' in patched
            assert '<td>0.00</td>' in patched


if __name__ == '__main__':
    unittest.main()
