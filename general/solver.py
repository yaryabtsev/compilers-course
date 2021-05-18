from general.display import Display
from general.parser import Parser
from tasks.task1 import LocalOptimization
from tasks.task2 import Dominator
from tasks.task3 import Phi


def solve(input: str, output: str, block_name: str = 'B1'):
    display = Display(output)
    display.block_name = block_name
    with open(input, 'r') as fin:
        parser = Parser(fin.read().split('\n'))
    parser.split_blocks()  # or parser.blocks = [[], ..., []] you can fill in the data yourself
    parser.lex_blocks()
    parser.graph()  # or parser.edges = [{1}, ..., {}] you can fill in the data yourself
    display.n = len(parser.lexemes)
    display.titles = ['Base Code', 'Control Flow Graph', 'Table of Values',
                      ' / '.join(['Pred', 'Dom', 'Idom', 'DF']),
                      'Dominator Tree'] * 3
    display.show_hyperlinks()
    display.show_code(parser.lexemes)
    display.show_graph(parser.edges)
    # TODO: task1:
    table = []
    for i in range(display.n):
        lo_block = LocalOptimization(parser.lexemes[i])
        table.append(lo_block.make_table())
    display.show_var_table(table)

    dominator = Dominator(parser.edges)
    # TODO: task2-spoilers
    table, columns = dominator.get_table()
    display.show_block_table(table, columns)
    display.show_graph(dominator.dom_edges)

    # TODO: task3:
    ...
    phi = Phi(parser.lexemes, dominator.dom_edges)
    display.show_spoiler(phi.globals_blocks())
    display.show_spoiler(phi.locate())
    display.show_phi_table(phi.table_new_phi())
    display.show_spoiler(phi.rename(0))
    phi.add_phi()
    display.show_code(phi.code_blocks)
    # TODO: task4:
    ...
    del display
