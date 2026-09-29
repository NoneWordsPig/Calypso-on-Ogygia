import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
 from PySide6.QtWidgets import QApplication
 from calypso.character.sprite_window import SpriteWindow
 from calypso.desktop.coordinate_mapper import ScreenTransform
 QT=True
except ImportError: QT=False
@unittest.skipUnless(QT,'PySide6 unavailable')
class SpriteTests(unittest.TestCase):
 def test_small_window(self):
  app=QApplication.instance() or QApplication([]); w=SpriteWindow(transform=ScreenTransform()); w.sync((100,100),'assets/calypso/walk_down/00.png'); self.assertLessEqual(w.height(),160); self.assertFalse(w.isFullScreen()); self.assertTrue(bool(w.windowFlags() & 0x8))
 def test_world_height_is_converted_to_logical_pixels(self):
  app=QApplication.instance() or QApplication([])
  transform=ScreenTransform(actual_primary_physical=(2560,1600),dpi=1.5)
  w=SpriteWindow(transform=transform,target_height=90)
  w.sync((100,100),'assets/calypso_v2/idle_down/00.png')
  self.assertEqual(w.height(),60)
 def test_night_sprite_uses_separate_shaded_frame(self):
  app=QApplication.instance() or QApplication([])
  w=SpriteWindow(target_height=38)
  path='assets/calypso/sleep/head_extracted.png'
  w.sync((100,100),path)
  day=w._pix.toImage()
  w.sync((100,100),path,night=True)
  night=w._pix.toImage()
  self.assertEqual(w.height(),38)
  self.assertNotEqual(day,night)
  self.assertEqual(set(key[2] for key in w._cache),{False,True})
 def test_sleep_pillow_anchor_and_fishing_feet_anchor(self):
  from calypso.navigation.manager import NavigationManager
  nav=NavigationManager(); transform=ScreenTransform()
  app=QApplication.instance() or QApplication([])
  w=SpriteWindow(transform=transform,target_height=40)
  w.sync(nav.visual_point('sleep'),'assets/calypso/sleep/head_extracted.png')
  source_top=transform.world_to_source(transform.logical_to_world((w.x(),w.y())))[1]
  self.assertAlmostEqual(source_top,483,delta=1)
  self.assertAlmostEqual(transform.world_to_source(transform.logical_to_world(
      (w.x()+w.width()/2,w.y()+w.height())))[1],503,delta=1)
  w.sync_target_height_world(nav.point('fishing'),
      'assets/calypso_v2/fishing/wait/00.png',245,anchor=(342,308))
  feet=(w.x()+342*w.width()/640,w.y()+308*w.height()/520)
  source_feet=transform.world_to_source(transform.logical_to_world(feet))
  self.assertAlmostEqual(source_feet[0],455,delta=1)
  self.assertAlmostEqual(source_feet[1],610,delta=1)
 def test_fishing_line_is_cached_as_a_separate_layer(self):
  app=QApplication.instance() or QApplication([])
  w=SpriteWindow(target_height=520)
  frame='assets/calypso_v2/fishing/wait/00.png'
  line='assets/calypso_v2/fishing/line/00.png'
  w.sync((100,100),frame)
  self.assertEqual(w._pix.toImage().pixelColor(49,475).alpha(),0)
  w.sync((100,100),frame,overlay=line)
  self.assertGreater(w._pix.toImage().pixelColor(49,475).alpha(),0)
  self.assertEqual(len(w._cache),2)
