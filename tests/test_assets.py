import json, hashlib, unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).parents[1]
class AssetTests(unittest.TestCase):
 def test_manifest(self):
  m=json.loads((ROOT/'assets/calypso/manifest.json').read_text())
  for n in ('walk_down','walk_up','walk_left','walk_right','idle_down','idle_up','work','sleep'): self.assertEqual(m['animations'][n]['count'],4)
 def test_frames(self):
  for p in (ROOT/'assets/calypso').rglob('*.png'):
   im=Image.open(p).convert('RGBA'); self.assertEqual(im.getchannel('A').getextrema()[0],0); self.assertTrue(all((r,g,b)==(0,0,0) for r,g,b,a in im.getdata() if a==0))
   self.assertGreater(im.getchannel('A').getbbox()[2],100)
 def test_computer(self):
  ims=[Image.open(ROOT/'assets/objects'/n).convert('RGBA') for n in ('computer_off.png','computer_on.png')]; self.assertNotEqual(hashlib.sha256(ims[0].tobytes()).hexdigest(),hashlib.sha256(ims[1].tobytes()).hexdigest())
  for im in ims: self.assertLess(im.width,1024); self.assertEqual(im.getchannel('A').getextrema()[0],0)
