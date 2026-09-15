import unittest
from calypso.desktop.desktop_host import DesktopHost, DesktopHostError

class FakeUser32:
    def __init__(self, fail=False): self.fail=fail; self.parents={}
    def FindWindowW(self, cls, title): return 10 if cls == 'Progman' else 0
    def SendMessageTimeoutW(self, *args): return 1
    def EnumWindows(self, callback, data):
        callback(20, data); callback(30, data); return 1
    def FindWindowExW(self, parent, after, cls, title):
        if cls == 'SHELLDLL_DefView' and parent == 20: return 21
        if cls == 'WorkerW' and after == 20: return 30
        return 0
    def SetLastError(self, value): self.error=value
    def GetLastError(self): return 5 if self.fail else 0
    def SetParent(self, hwnd, parent):
        if self.fail: return 0
        old=self.parents.get(hwnd, 99); self.parents[hwnd]=parent; return old

class DesktopHostTests(unittest.TestCase):
    def test_selects_sibling_and_restores_parent(self):
        host=DesktopHost(FakeUser32()); self.assertEqual(host.find_workerw(),30)
        self.assertTrue(host.attach(100)); self.assertEqual(host.user32.parents[100],30)
        self.assertTrue(host.detach(100)); self.assertEqual(host.user32.parents[100],99)
    def test_setparent_failure(self):
        with self.assertRaises(DesktopHostError): DesktopHost(FakeUser32(True)).attach(100)
    def test_non_windows_is_safe(self):
        with self.assertRaises(DesktopHostError): DesktopHost(None).attach(100)

if __name__ == '__main__': unittest.main()
