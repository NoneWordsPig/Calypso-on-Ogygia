import unittest
import math
from pathlib import Path
from calypso.navigation.manager import NavigationManager
from calypso.desktop.coordinate_mapper import ScreenTransform

class NavigationCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nav = NavigationManager()
        cls.names = tuple(cls.nav.points)

    def test_all_pois_are_connected(self):
        for source in self.names:
            for target in self.names:
                self.assertTrue(self.nav.go_to(target, self.nav.point(source)))

    def test_unknown_location_is_clear(self):
        with self.assertRaisesRegex(KeyError, "Unknown location"):
            self.nav.go_to("not-a-place", self.nav.point("spawn"))

    def test_off_grid_start_is_recovered(self):
        path = self.nav.go_to("computer", (-100, -100))
        self.assertEqual(path[0], (-100, -100))
        self.assertEqual(path[-1], self.nav.point("computer"))

    def test_paths_do_not_corner_cut(self):
        for source in self.names:
            for target in self.names:
                path = self.nav.go_to(target, self.nav.point(source))
                cells = [self.nav._cell(p) for p in path]
                # POI coordinates are interaction pixels and can lie just outside
                # their route cell; validate all grid-to-grid route transitions.
                for a, b in zip(cells[1:], cells[2:]):
                    if a[0] != b[0] and a[1] != b[1]:
                        if max(abs(a[0]-b[0]), abs(a[1]-b[1])) == 1:
                            self.assertTrue(self.nav._open((a[0], b[1])))
                            self.assertTrue(self.nav._open((b[0], a[1])))

    def test_source_world_roundtrip(self):
        transform = ScreenTransform()
        for point in ((0, 0), (574, 263), (1312, 816)):
            result = transform.world_to_source(transform.source_to_world(point))
            self.assertAlmostEqual(result[0], point[0])
            self.assertAlmostEqual(result[1], point[1])

    def test_fishing_feet_are_on_walkable_sand_and_sleep_has_pillow_anchor(self):
        self.assertTrue(self.nav.is_walkable_world(self.nav.point("fishing")))
        self.assertEqual(self.nav.transform.world_to_source(self.nav.point("fishing")),
                         (455.0, 610.0))
        self.assertEqual(self.nav.transform.world_to_source(self.nav.visual_point("sleep")),
                         (1074.0, 503.0))
        self.assertEqual(self.nav.transform.world_to_source(self.nav.point("bed")),
                         (1074.0, 513.0))

    def test_path_has_no_repeated_points_and_ends_at_interaction(self):
        for source in self.names:
            for target in self.names:
                start = self.nav.point(source)
                path = self.nav.go_to(target, start)
                self.assertEqual(path[0], start)
                self.assertEqual(path[-1], self.nav.point(target))
                self.assertTrue(all(a != b for a, b in zip(path, path[1:])))
                for a, b in zip(path, path[1:]):
                    count = max(1, math.ceil(math.dist(a, b) / 4))
                    for index in range(count + 1):
                        fraction = index / count
                        sample = (a[0] + (b[0] - a[0]) * fraction,
                                  a[1] + (b[1] - a[1]) * fraction)
                        self.assertTrue(self.nav.is_walkable_world(sample),
                                        (source, target, sample))

if __name__ == "__main__":
    unittest.main()
