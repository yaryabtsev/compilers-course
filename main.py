import argparse

from general.solver import solve

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compilers Solver')
    parser.add_argument(
        '--input',
        type=str,
        default='input/test01.txt',
        help='provide an path to the data file (default: input/test01.txt)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output/',
        help='provide an path to the output directory (default: output/test01/)'
    )
    parser.add_argument(
        '--node',
        type=str,
        default='A',
        help='specify the name of the first block (default: A)'
    )
    args = parser.parse_args()
    input, output = args.input, args.output
    solve(input, output)
