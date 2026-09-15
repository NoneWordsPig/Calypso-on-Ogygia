import unittest
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

if __name__ == "__main__":
    unittest.main()
