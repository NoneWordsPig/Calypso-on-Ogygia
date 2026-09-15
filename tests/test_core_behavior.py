import unittest
from calypso.behavior.manager import BehaviorManager
from calypso.behavior.states import State
class C:
 position=(0,0); running=False
 def set_path(self,p): self.path=p
class N:
 points={'computer':(1,1),'bed':(2,2),'spawn':(0,0)}
 def go_to(self,n,s): return [self.points[n]]
class T:
 minutes=480
 def advance(self,x): return []
 def is_sleep_period(self): return False
class K:
 on=False
 def turn_on(self): self.on=True
 def turn_off(self): self.on=False
class BehaviorTests(unittest.TestCase):
 def setUp(self): self.c=C(); self.k=K(); self.b=BehaviorManager(self.c,self.k,T(),N())
 def test_task(self): self.b.task_started(); self.assertFalse(self.k.on); self.b.arrived('computer'); self.assertTrue(self.k.on)
 def test_finish(self): self.b.task_started(); self.b.task_finished(); self.assertFalse(self.k.on); self.assertEqual(self.b.target,'spawn')
 def test_sleep_due(self): self.b.sleep_due=True; self.b.task=True; self.b.task_finished(); self.assertEqual(self.b.target,'bed')
 def test_bed(self): self.b.arrived('bed'); self.assertEqual(self.b.state,State.SLEEPING)
