from general.display import Display
from general.parser import Parser
from tasks.task1 import LocalOptimization
from tasks.task2 import Dominator
from tasks.task3 import Phi
from tasks.task4 import Regions


def solve(input: str, output: str, block_name: str = 'A', blocks=None, edges=None):
    display = Display(output)
    display.block_name = block_name
    if input:
        with open(input, 'r') as fin:
            parser = Parser(fin.read().split('\n'))
    else:
        parser = Parser([''])
    if blocks:
        parser.blocks = blocks
    else:
        parser.split_blocks()
    parser.lex_blocks()
    if edges:
        parser.edges = edges
    else:
        parser.graph()
    n = len(parser.lexemes)
    display.n = n
    display.titles = ['Base Code', 'Control Flow Graph', 'Table of Values',
                      ' / '.join(['Pred', 'Dom', 'Idom', 'DF']),
                      'Dominator Tree', 'Globals & Blocks', 'Insert a phi-function', 'Partially Truncated SSA-Form',
                      'Regions', 'Control Tree', 'Classification', 'Gen-Kill', 'Transfer function']
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

    # TODO: task3-stack
    phi = Phi(parser.lexemes, dominator)
    spoilers = phi.globals_blocks()
    display.show_block_table(*phi.table_gb(), spoilers)
    spoilers = phi.locate()
    display.show_code(phi.code_blocks, spoilers)
    # display.show_block_table(*phi.table_new_phi(), spoilers)
    spoilers = phi.rename(0)
    display.show_code(phi.code_blocks, spoilers)
    # TODO: task4:
    regions = Regions(dominator, parser.lexemes)
    display.show_graphs(list(regions.find_regions()))
    display.show_control_tree(regions.control_tree)
    display.show_block_table([['Region'] + regions.classification], ['Class', 'Area-Node', 'Area-Body', 'Area-Loop'])
    display.show_block_table(*regions.gen_kill())
    display.show_block_table(*regions.transfer_function())
    del display
