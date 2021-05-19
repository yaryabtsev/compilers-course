import copy

from general.display import Display
from general.parser import Parser
from tasks.task1 import LocalOptimization
from tasks.task2 import Dominator
from tasks.task3 import Phi


def solve(input: str, output: str, block_name: str = 'A'):
    display = Display(output)
    display.block_name = block_name
    with open(input, 'r') as fin:
        parser = Parser(fin.read().split('\n'))
    parser.split_blocks()  # or parser.blocks = [[], ..., []] you can fill in the data yourself
    parser.lex_blocks()
    parser.graph()  # or parser.edges = [{1}, ..., {}] you can fill in the data yourself
    n = len(parser.lexemes)
    display.n = n
    display.titles = ['Base Code', 'Control Flow Graph', 'Table of Values',
                      ' / '.join(['Pred', 'Dom', 'Idom', 'DF']),
                      'Dominator Tree', 'Globals & Blocks', 'Needs a phi-function', 'Partially Truncated SSA-Form']
    display.show_hyperlinks()
    display.show_code(parser.lexemes)
    display.show_graph(parser.edges)

    table = []
    for i in range(n):
        lo_block = LocalOptimization(parser.lexemes[i])
        table.append(lo_block.make_table())
    display.show_var_table(table)
    # TODO: task1-Input/Output
    dominator = Dominator(parser.edges)
    # TODO: task2-spoilers
    display.show_block_table(*dominator.get_table())
    display.show_graph(dominator.dom_edges)

    # TODO: task3 (spoilers, rename, add_phi)
    phi = Phi(parser.lexemes, dominator)
    spoilers = phi.globals_blocks()
    display.show_block_table(*phi.table_gb(), spoilers)
    spoilers = phi.locate()
    display.show_block_table(*phi.table_new_phi(), spoilers)
    spoilers = phi.rename(0)
    display.show_code(phi.code_blocks, spoilers)
    # TODO: task4:
    ...
    del display
