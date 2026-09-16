try:
 from PySide6.QtWidgets import QWidget
 from PySide6.QtCore import Qt
 from PySide6.QtGui import QPixmap,QPainter,QRegion,QBitmap
 from ..desktop.window_styles import apply_native_styles
 from ..desktop.coordinate_mapper import ScreenTransform
 class SpriteWindow(QWidget):
  def __init__(self,manifest=None,transform=None,parent=None,interactive=False,target_height=88):
   super().__init__(parent);self.transform=transform or ScreenTransform();self._cache={};self._key=None;self._last_pos=None
   self.target_height=int(target_height);self.setWindowFlags(Qt.FramelessWindowHint|Qt.Tool|(Qt.WindowDoesNotAcceptFocus if not interactive else Qt.Widget));self.setAttribute(Qt.WA_TranslucentBackground);apply_native_styles(self,interactive)
  def sync(self,world_pos,frame):
   logical_h=max(1,round(self.target_height*self.transform.actual_primary_physical[1]/self.transform.world_size[1]/self.transform.dpi)); key=(str(frame),logical_h)
   if key not in self._cache:
    raw=QPixmap(key[0]);h=logical_h;pix=raw.scaled(round(raw.width()*h/raw.height()),h,Qt.IgnoreAspectRatio,Qt.FastTransformation);self._cache[key]=(pix,QBitmap.fromImage(pix.toImage().createAlphaMask()))
   self._pix,self._mask=self._cache[key]
   if self.size()!=self._pix.size():self.resize(self._pix.size());self.setMask(QRegion(self._mask))
   p=self.transform.world_to_logical(world_pos);pos=(round(p[0]-self.width()/2),round(p[1]-self.height()))
   if pos!=self._last_pos:self.move(*pos);self._last_pos=pos
   if key!=self._key:self.update();self._key=key
  def sync_target_height_world(self, world_pos, frame, target_height):
   self.target_height=int(target_height); self.sync(world_pos, frame)
  def paintEvent(self,event):
   if hasattr(self,'_pix'):QPainter(self).drawPixmap(0,0,self._pix)
except ImportError:
 class SpriteWindow:
  def __init__(self,*a,**k):raise RuntimeError('PySide6 is required for SpriteWindow')
