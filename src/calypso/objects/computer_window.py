from pathlib import Path
from ..character.sprite_window import SpriteWindow
class ComputerWindow(SpriteWindow):
    def __init__(self, transform=None, navigation=None, parent=None, target_height=48):
        super().__init__(transform=transform, parent=parent, target_height=target_height); self.navigation=navigation
        from ..desktop.window_styles import apply_native_styles
        apply_native_styles(self, interactive=False, click_through=True)
        from ..config import PROJECT_ROOT; self._paths={False:str(PROJECT_ROOT/'assets/objects/computer_off.png'),True:str(PROJECT_ROOT/'assets/objects/computer_on.png')}; self._last=None
    def sync_state(self, on=False):
        if on != self._last:
            self._last=on; point=self.navigation.point('computer') if self.navigation else (0,0); self.sync(point,self._paths[on])
