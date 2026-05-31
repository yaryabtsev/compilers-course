from general.display import Display
from general.parser import Parser
from tasks.acyclic_region_preview import AcyclicRegionSummaryPreview
from tasks.branch_conditions import SymbolicBranchDump
from tasks.local_value_tables import LocalValueTable
from tasks.dominators import Dominator, PostDominator
from tasks.query_cost_estimation import HotVariableDump
from tasks.quantified_patterns import QuantifiedPatternPreview
from tasks.ssa import Phi
from tasks.regions import Regions
from tasks.state_merge_preview import JoinMergePreview
from tasks.symbolic_scope_stubs import UnsupportedSymbolicStageDump
from general.viewer import now_iso, write_dataset_metadata


def solve(input: str, output: str, block_name: str = 'A', blocks=None, edges=None, qadd_beta: float = 0.5):
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
    display.titles = ['Base MIR', 'Control Flow Graph', 'Symbolic Branch Conditions',
                      'Q_add / Q_t Approximation', 'Quantified Pattern Preview',
                      'Symbolic Execution Scope Stubs',
                      'Local Value Tables', 'Input / Output Sets',
                      ' / '.join(['Pred', 'Dom', 'Idom', 'DF']),
                      'Dominator Tree', 'Postdominators & Control Dependence',
                      'Globals & Blocks', 'Phi Placement', 'Phi-Inserted Code', 'Partially Truncated SSA Form',
                      'SSA Checks', 'Join Merge Preview', 'Cycle-Based Region Reduction',
                      'Acyclic Region Summary Preview',
                      'Control Tree', 'Region Classification', 'Gen / Kill',
                      'Region Transfer Functions (Structural)']
    display.notes = ['MIR / blocks', 'CFG edges', 'SE forks', 'QCE recurrence',
                     'node tree / pattern inference', 'unsupported papers',
                     'LVN table', 'local data-flow',
                     'dominators / DF', 'dom tree', 'postdom / CD',
                     'SSA globals', 'DF worklist', 'phi code', 'SSA rename',
                     'partial audit', 'state merging', 'cycle regions', 'veritesting idea',
                     'region tree', 'area classes', 'reaching defs', 'structural transfer']
    display.show_hyperlinks()
    display.show_code(parser.lexemes)
    display.show_graph(parser.edges)
    display.show_block_table(*SymbolicBranchDump(parser.lexemes, parser.edges, display.name).table())
    hot_variables = HotVariableDump(parser.lexemes, parser.edges, display.name, beta=qadd_beta)
    display.show_block_table_group(hot_variables.tables(output))
    display.show_block_table_group(QuantifiedPatternPreview(parser.lexemes, parser.edges, display.name).tables())
    display.show_block_table(*UnsupportedSymbolicStageDump().table())

    table = []
    for i in range(n):
        lo_block = LocalValueTable(parser.lexemes[i])
        table.append(lo_block.make_table())
    display.show_var_table(table)
    display.show_block_table(*LocalValueTable.input_output_table(parser.lexemes))
    dominator = Dominator(parser.edges)
    display.show_block_table(*dominator.get_table())
    display.show_graph(dominator.dom_edges)
    post_dominator = PostDominator(parser.edges)
    display.show_block_table(*post_dominator.get_table())

    phi = Phi(parser.lexemes, dominator)
    spoilers = phi.globals_blocks()
    display.show_block_table(*phi.table_gb(), spoilers)
    spoilers = phi.locate()
    display.show_block_table(*phi.table_new_phi(), spoilers)
    display.show_code(phi.code_blocks)
    spoilers = phi.rename(0)
    display.show_code(phi.code_blocks, spoilers)
    display.show_block_table(*phi.checks())
    display.show_block_table(*JoinMergePreview(phi, dominator, display.name).table())

    regions = Regions(dominator, parser.lexemes)
    display.show_graphs(list(regions.find_regions()))
    display.show_block_table(*AcyclicRegionSummaryPreview(
        parser.lexemes, parser.edges, post_dominator, display.name).table())
    display.show_control_tree(regions.control_tree)
    display.show_block_table([['Region'] + regions.classification], ['Class', 'Area-Node', 'Area-Body', 'Area-Loop'])
    display.show_block_table(*regions.gen_kill())
    display.show_block_table(*regions.transfer_function())
    processed_at = now_iso()
    sections_count = len(display.titles)
    display.close()
    write_dataset_metadata(output, input, block_name, n, sections_count, processed_at)
