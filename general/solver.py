from general.display import Display
from general.parser import Parser
from tasks.task2 import Dominator
from tasks.task3 import Phi


def solve(input: str, output: str):
    display = Display(output)
    with open(input, 'r') as fin:
        parser = Parser(fin.read().split('\n'))
    n = len(parser.lexemes)
    titles = ['Base Code', 'Control Flow Graph', ' / '.join(['Pred', 'Dom', 'Idom', 'DF']), 'Dominator Tree']
    display.show_hyperlinks(titles)
    title_id = 0
    display.show_code(parser.lexemes, titles[title_id], title_id)
    title_id += 1
    display.show_graph(parser.edges, titles[title_id], title_id)
    title_id += 1
    # TODO: task1:
    ...

    dominator = Dominator(parser.edges)
    # TODO: task2-spoilers
    table, columns = dominator.get_table()
    display.show_block_table(table, columns, n, titles[title_id], title_id)
    title_id += 1
    display.show_graph(dominator.dom_edges, titles[title_id], title_id)
    title_id += 1

    # TODO: task3:
    ...
    Phi(parser.lexemes, dominator.dom_edges)

    # TODO: task4:
    ...
    del display
