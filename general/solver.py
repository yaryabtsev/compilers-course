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
    display.titles = ['Base MIR', 'Control Flow Graph', 'Local Value Tables', 'Input / Output Sets',
                      ' / '.join(['Pred', 'Dom', 'Idom', 'DF']),
                      'Dominator Tree', 'Postdominators & Control Dependence',
                      'Globals & Blocks', 'Phi Placement', 'Phi-Inserted Code', 'Partially Truncated SSA Form',
                      'SSA Checks', 'Region Reduction', 'Control Tree', 'Region Classification', 'Gen / Kill',
                      'Region Transfer Functions']
    display.show_hyperlinks()
    display.show_code(parser.lexemes)
    display.show_graph(parser.edges)

    table = []
    for i in range(n):
        lo_block = LocalOptimization(parser.lexemes[i])
        table.append(lo_block.make_table())
    display.show_var_table(table)
    display.show_placeholder('The lectures define basic-block Input and Output sets for local optimization, '
                             'but this project currently builds only per-block value tables.')
    dominator = Dominator(parser.edges)
    display.show_block_table(*dominator.get_table())
    display.show_graph(dominator.dom_edges)
    display.show_placeholder('Postdominators, reverse dominance frontiers, and control-dependence tables are '
                             'lecture topics that are not implemented yet.')

    phi = Phi(parser.lexemes, dominator)
    spoilers = phi.globals_blocks()
    display.show_block_table(*phi.table_gb(), spoilers)
    spoilers = phi.locate()
    display.show_block_table(*phi.table_new_phi(), spoilers)
    display.show_code(phi.code_blocks)
    spoilers = phi.rename(0)
    display.show_code(phi.code_blocks, spoilers)
    display.show_placeholder('The report does not currently validate SSA invariants such as unique definitions '
                             'for every SSA name or predecessor-ordered phi arguments.')

    regions = Regions(dominator, parser.lexemes)
    display.show_graphs(list(regions.find_regions()))
    display.show_control_tree(regions.control_tree)
    display.show_block_table([['Region'] + regions.classification], ['Class', 'Area-Node', 'Area-Body', 'Area-Loop'])
    display.show_block_table(*regions.gen_kill())
    display.show_block_table(*regions.transfer_function())
    del display
