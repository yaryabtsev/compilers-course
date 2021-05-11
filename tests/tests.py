import os
import unittest

from general.solver import solve


class MyTestCase(unittest.TestCase):
    @staticmethod
    def test_solve_input():
        for file_name in os.listdir('input/'):
            assert solve(f'input/{file_name}', f"output/{file_name.split('.')[0]}/") is None


if __name__ == '__main__':
    unittest.main()
