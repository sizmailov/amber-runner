from amber_runner.MD import Step
from remote_runner import Task
from pathlib import Path


class SayWorld(Step):
    def __init__(self, name):
        Step.__init__(self, name)
        self.greeting = "World!"

    def run(self, md):
        print(self.greeting)


md = Task.load(Path("P0/state.dill"))
md.greet = SayWorld("greet")
md.save(md.wd / md.state_filename)
