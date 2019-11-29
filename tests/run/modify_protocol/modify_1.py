from remote_runner import Task
from pathlib import Path

md = Task.load(Path("P0/state.dill"))
md.greet.greeting = "FooBar"
md.greet.is_complete = False
md.save(md.wd / md.state_filename)
