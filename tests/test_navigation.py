"""Navigation tests: the checked-in walkable grid must connect all POIs."""
import unittest

from app.config import ROOT
from app.navigation import Navigation

NAV = ROOT / "data" / "navigation.json"
POIS = ["computer", "bed", "fishing", "campfire", "spawn"]


class TestNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nav = Navigation(NAV)

    def test_grid_has_walkable_cells(self):
        self.assertGreater(self.nav._free_cells.__len__(), 500)

    def test_pois_have_walkable_neighbors(self):
        for name in POIS:
            self.assertIsNotNone(self.nav.nearest_walkable(self.nav.poi(name)), name)

    def test_all_poi_pairs_reachable(self):
        for i in range(len(POIS)):
            for j in range(i + 1, len(POIS)):
                a = self.nav.poi(POIS[i])
                b = self.nav.poi(POIS[j])
                path = self.nav.find_path(a, b)
                self.assertGreaterEqual(len(path), 2, f"{POIS[i]}->{POIS[j]}")
                self.assertTrue(self.nav.is_walkable(path[-1]), f"{POIS[i]}->{POIS[j]} end off-grid")
                for pt in path[1:-1]:
                    self.assertTrue(self.nav.is_walkable(pt), f"off-road point {pt}")

    def test_path_points_on_road(self):
        a = self.nav.poi("computer")
        b = self.nav.poi("bed")
        path = self.nav.find_path(a, b)
        for pt in path:
            self.assertTrue(self.nav.is_walkable(pt), f"off-road point {pt}")


if __name__ == "__main__":
    unittest.main()
