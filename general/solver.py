from general.display import Display
from general.parser import Parser
from tasks.task2 import Dominator


def solve(input: str, output: str):
    display = Display(output)
    with open(input, 'r') as fin:
        parser = Parser(fin.read().split('\n'))
    n = len(parser.lexemes)
    display.show_code(parser.lexemes, 'Base Code')
    display.show_graph(parser.edges, 'Control Flow Graph')
    # TODO: task1:
    ...
    dominator = Dominator(parser.edges)
    # TODO: task2-spoilers
    table, columns = dominator.get_table()
    display.show_block_table(table, columns, n, ' / '.join(['Pred', 'Dom', 'Idom', 'DF']))
    display.show_graph(dominator.dom_edges, 'Dominator Tree')
    # TODO: task3:
    ...
    # TODO: task4:
    ...
    del display
