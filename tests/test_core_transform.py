import unittest
from calypso.desktop.coordinate_mapper import ScreenTransform
class TransformTests(unittest.TestCase):
 def test_roundtrips(self):
  for d in (1.,1.5,1.75):
   t=ScreenTransform(dpi=d,actual_primary_physical=(1920,1080))
   p=(321.,654.); self.assertEqual(t.physical_to_logical(t.logical_to_physical(p)),p)
   self.assertEqual(t.physical_to_world(t.world_to_physical(p)),p)
   self.assertAlmostEqual(t.logical_to_world(t.world_to_logical(p))[0],p[0]); self.assertAlmostEqual(t.logical_to_world(t.world_to_logical(p))[1],p[1])
 def test_source_world(self):
  t=ScreenTransform(); self.assertEqual(t.source_to_world((0,0)),(0.,0.)); self.assertEqual(t.source_to_world((1312,816)),(2560.,1600.))
