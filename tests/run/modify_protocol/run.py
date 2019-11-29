from pathlib import Path
import remote_runner
from remote_runner import Pool, LocalWorker, Task

workers = [
    LocalWorker()
]

tasks = [
    Task.load(Path("P0/state.dill"))
]

Pool(workers).run(tasks)
