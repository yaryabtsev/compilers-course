from general.display import Display
from general.parser import Parser


def solve(input: str, output: str):
    display = Display(output)
    with open(input, 'r') as fin:
        parser = Parser(fin.read().split('\n'))
    display.show_code(parser.lexemes, 'Base Code')
    display.show_graph(parser.edges, 'Control Flow Graph')
    # TODO: task1, task2, task3, task4
    del display
