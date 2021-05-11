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
        default='output/test01/',
        help='provide an the path to the output directory (default: output/test01/)'
    )
    args = parser.parse_args()
    input, output = args.input, args.output
    solve(input, output)
