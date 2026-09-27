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
