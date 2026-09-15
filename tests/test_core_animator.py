import unittest
from pathlib import Path
from calypso.character.animator import Animator
class AnimatorTests(unittest.TestCase):
 def setUp(self): self.a=Animator()
 def test_directions(self):
  for d in ('down','up','left','right'):
   self.assertTrue(self.a.select(d)); self.assertTrue(self.a.select(d,True))
 def test_alias_special_and_path(self):
  self.a.select('left'); self.assertEqual(self.a.state,'idle_left'); self.assertEqual(self.a._entry().get('count'),4); self.a.set_state('work'); self.assertIn('assets',self.a.frame_path()); self.a.set_state('sleep'); self.assertTrue(Path(self.a.frame_path()).exists())
 def test_timing_and_run(self):
  self.a.select('down',True); self.a.tick(.5); self.assertEqual(self.a.frame,0); self.a.tick(.2); self.assertEqual(self.a.frame,1); self.a.tick(.5,True); self.assertEqual(self.a.frame,0)
