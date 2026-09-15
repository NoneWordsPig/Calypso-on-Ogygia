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
