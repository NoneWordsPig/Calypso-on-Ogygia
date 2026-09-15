import ctypes
class DesktopHostError(RuntimeError): pass
class DesktopHost:
 def __init__(self,user32=None):
  self.user32=user32 or (ctypes.windll.user32 if hasattr(ctypes,'windll') else None); self._parents={}
  if self.user32 is not None:
   for name,restype,args in [('FindWindowW',ctypes.c_void_p,[ctypes.c_wchar_p,ctypes.c_wchar_p]),('FindWindowExW',ctypes.c_void_p,[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p]),('SetParent',ctypes.c_void_p,[ctypes.c_void_p,ctypes.c_void_p]),('SendMessageTimeoutW',ctypes.c_void_p,None),('EnumWindows',ctypes.c_int,None)]:
    fn=getattr(self.user32,name,None)
    if fn is not None:
     try: fn.restype=restype; fn.argtypes=args
     except (AttributeError,TypeError): pass
 @property
 def available(self): return self.user32 is not None
 def find_workerw(self):
  if not self.available:return None
  u=self.user32;p=u.FindWindowW('Progman',None)
  if p:u.SendMessageTimeoutW(p,0x052C,0,0,0,1000,None)
  found=[]; cb=getattr(ctypes,'WINFUNCTYPE',ctypes.CFUNCTYPE)(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
  def each(h,_):
   if u.FindWindowExW(h,0,'SHELLDLL_DefView',None):found.append(h)
   return True
  try:u.EnumWindows(cb(each),0)
  except (AttributeError,TypeError):return None
  if found:
   shell_host=found[0]
   sibling=u.FindWindowExW(0,shell_host,'WorkerW',None)
   return sibling or shell_host
  return p or None
 def attach(self,hwnd):
  if not self.available:raise DesktopHostError('desktop integration is only available on Windows')
  parent=self.find_workerw()
  if not parent:raise DesktopHostError('could not locate desktop WorkerW')
  try: self.user32.SetLastError(0)
  except AttributeError: pass
  old=self.user32.SetParent(int(hwnd),int(parent))
  error=getattr(self.user32,'GetLastError',lambda:0)()
  if not old and error: raise DesktopHostError('SetParent failed')
  self._parents[int(hwnd)]=old; return True
 def detach(self,hwnd):
  if not self.available or int(hwnd) not in self._parents:return False
  h=int(hwnd);self.user32.SetParent(h,self._parents.pop(h) or 0);return True
 def cleanup(self):
  for h in list(self._parents):self.detach(h)
