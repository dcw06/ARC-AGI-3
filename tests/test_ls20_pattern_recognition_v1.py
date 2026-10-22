"""Visible glyph discovery, exact scaling, rotation and fail-closed ambiguity."""
from copy import deepcopy
import unittest

from research.ls20_pattern_goal_v1.patterns import (
    compare_patterns, locate_panels, read_panel)


ASYMMETRIC = [[1, 1, 1], [1, 0, 0], [1, 0, 1]]


def rotate(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


def panel(grid, matrix, *, left, top, scale=1, margin=1):
    width = len(matrix[0])*scale+2*margin
    height = len(matrix)*scale+2*margin
    assert width == height
    for y in range(top, top+height):
        for x in range(left, left+width):
            grid[y][x] = 5
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            for dy in range(scale):
                for dx in range(scale):
                    grid[top+margin+y*scale+dy][left+margin+x*scale+dx] = 9 if value else 5
    return [left, top, left+width-1, top+height-1]


def board():
    grid = [[4]*64 for _ in range(64)]
    reference = panel(grid, ASYMMETRIC, left=4, top=42, scale=2, margin=2)
    destination = panel(grid, rotate(ASYMMETRIC), left=30, top=8, margin=2)
    return grid, reference, destination


class PatternRecognition(unittest.TestCase):
    def test_discovers_panels_without_locations_and_preserves_disconnected_mark(self):
        grid, reference, destination = board()
        found = locate_panels(grid)
        self.assertEqual(found['reference']['bbox'], reference)
        self.assertEqual(found['destination']['bbox'], destination)
        self.assertEqual(found['reference']['pattern'], ASYMMETRIC)
        self.assertEqual(found['destination']['pattern'], rotate(ASYMMETRIC))
        self.assertEqual(found['reference']['scale'], 2)
        self.assertEqual(found['destination']['scale'], 1)
        self.assertEqual(found['destination']['center'], [33, 11])
        self.assertEqual(found['reference']['center'], [8.5, 46.5])

    def test_translation_and_common_display_rescaling_do_not_change_recognition(self):
        grid = [[4]*64 for _ in range(64)]
        panel(grid, ASYMMETRIC, left=6, top=34, scale=4, margin=2)
        panel(grid, rotate(ASYMMETRIC), left=35, top=5, scale=2, margin=2)
        found = locate_panels(grid)
        self.assertEqual(found['reference']['pattern'], ASYMMETRIC)
        self.assertEqual(found['destination']['pattern'], rotate(ASYMMETRIC))
        self.assertEqual((found['reference']['scale'], found['destination']['scale']), (4, 2))

    def test_comparison_distinguishes_current_match_from_available_rotation(self):
        a = {'pattern': ASYMMETRIC}
        b = {'pattern': rotate(ASYMMETRIC)}
        self.assertEqual(compare_patterns(a, b), {'matched': False, 'clockwise_quarter_turns': [1]})
        self.assertEqual(compare_patterns(b, b), {'matched': True, 'clockwise_quarter_turns': [0]})

    def test_preserves_rotation_ambiguity_for_symmetric_glyph(self):
        symmetric = {'pattern': [[1, 1, 1], [1, 0, 1], [1, 1, 1]]}
        self.assertEqual(compare_patterns(symmetric, symmetric),
                         {'matched': True, 'clockwise_quarter_turns': [0, 1, 2, 3]})

    def test_holes_survive_lossless_reduction(self):
        matrix = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
        grid = [[4]*64 for _ in range(64)]
        bounds = panel(grid, matrix, left=10, top=10, scale=3, margin=2)
        found = read_panel(grid, bounds)
        self.assertEqual(found['pattern'], matrix)
        self.assertEqual(found['scale'], 3)
        self.assertEqual(len([row for row in found['pattern'] if 0 in row]), 1)

    def test_nonuniform_block_pixels_are_not_smoothed_away(self):
        grid, reference, _ = board()
        grid[44][6] = 5
        found = read_panel(grid, reference)
        self.assertEqual(found['scale'], 1)
        with self.assertRaises(ValueError):
            locate_panels(grid)

    def test_equal_scale_panel_roles_refuse(self):
        grid = [[4]*64 for _ in range(64)]
        panel(grid, ASYMMETRIC, left=4, top=4)
        panel(grid, rotate(ASYMMETRIC), left=25, top=25)
        with self.assertRaises(ValueError):
            locate_panels(grid)

    def test_extra_valid_panel_is_ambiguous(self):
        grid, _, _ = board()
        panel(grid, ASYMMETRIC, left=43, top=43)
        with self.assertRaises(ValueError):
            locate_panels(grid)

    def test_missing_foreground_unexpected_color_and_cut_border_refuse(self):
        grid, reference, _ = board()
        for mutation in ('empty', 'color', 'border'):
            changed = deepcopy(grid)
            if mutation == 'empty':
                for y in range(reference[1], reference[3]+1):
                    for x in range(reference[0], reference[2]+1):
                        changed[y][x] = 5
            elif mutation == 'color':
                changed[reference[1]+1][reference[0]+1] = 12
            else:
                changed[reference[1]][reference[0]+1] = 9
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                read_panel(changed, reference)
            with self.subTest(discovery=mutation), self.assertRaises(ValueError):
                locate_panels(changed)

    def test_frozen_reference_read_does_not_require_destination_to_remain_visible(self):
        grid, reference, destination = board()
        initial = locate_panels(grid)
        panel(grid, rotate(ASYMMETRIC), left=reference[0], top=reference[1], scale=2, margin=2)
        grid[destination[1]+2][destination[0]+2] = 12
        reread = read_panel(grid, reference)
        self.assertTrue(compare_patterns(reread, initial['destination'])['matched'])
        with self.assertRaises(ValueError):
            locate_panels(grid)

    def test_comparison_rejects_reflection_without_equivalent_rotation(self):
        chiral = [[1, 1, 1], [1, 0, 0], [0, 1, 0]]
        reflected = [row[::-1] for row in chiral]
        self.assertEqual(compare_patterns({'pattern': chiral}, {'pattern': reflected}),
                         {'matched': False, 'clockwise_quarter_turns': []})

    def test_invalid_matrices_and_bounds_refuse(self):
        grid, _, _ = board()
        for bounds in ([1, 1, 2, 3], [True, 1, 4, 4], [-1, 1, 3, 3], [3, 3, 1, 1]):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                read_panel(grid, bounds)
        for matrix in ([], [[0]], [[True]], [[1], [1, 0]], [[2]]):
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                compare_patterns({'pattern': matrix}, {'pattern': ASYMMETRIC})


if __name__ == '__main__':
    unittest.main()
