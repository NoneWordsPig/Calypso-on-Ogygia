class FakeAgentBridge:
 def __init__(self,manager): self.manager=manager
 def fake_task_start(self): self.manager.task_started()
 def fake_task_finish(self): self.manager.task_finished()
 start=fake_task_start
 finish=fake_task_finish
