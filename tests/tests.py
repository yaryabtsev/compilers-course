import os
import unittest

from general.solver import solve


class MyTestCase(unittest.TestCase):
    @staticmethod
    def test_solve_input():
        for file_name in os.listdir('input/'):
            assert solve(f'input/{file_name}', f"output/{file_name.split('.')[0]}/") is None

    @staticmethod
    def test_user_input():
        blocks = [[],
                  ['param c', 'i <-- #0', 'a <-- -, #2, i', 'b <-- +, #2, i'],
                  ['a <-- +, a, i'],
                  ['j <-- +, a, b', 'a <-- +, a, b', 'b <-- j'],
                  ['i <-- +, #1, i'],
                  ['a <-- +, a, #1', 'b <-- +, b, c', 'a <-- +, b, i', 'b <-- a'],
                  []]
        edges = [{1}, {2, 3}, {5}, {3, 4}, {2, 5}, {6}, set()]
        assert solve('', 'output/test05/', 'R1', blocks, edges) is None

    @staticmethod
    def test_regions():
        blocks = [[] for _ in range(10)]
        edges = [{1}, {2, 9}, {3, 8}, {4, 5}, {7}, {6, 3}, {7}, {2}, {1}, set()]
        assert solve('', 'output/test06/', 'B1', blocks, edges) is None

    @staticmethod
    def test_regions_reverse():
        blocks = [[] for _ in range(10)]
        edges = [{8}, {8}, {7}, {2}, {3, 6}, {2}, {4, 5}, {6, 1}, {7, 9}, set()]
        assert solve('', 'output/test07/', 'B1', blocks, edges) is None

    @staticmethod
    def test_task4():
        blocks = [[],
                  ['i <-- -, m, #1', 'j <-- n', 'a <-- u1'],
                  ['i <-- +, i, #1'],
                  ['a <-- u2'],
                  ['j <-- u3'],
                  [], []]
        edges = [{1}, {2}, {3, 4}, {4, 5}, {2, 5}, {6}, set()]
        assert solve('', 'output/test08/', 'B1', blocks, edges) is None


if __name__ == '__main__':
    unittest.main()
