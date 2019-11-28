from pathlib import Path
import remote_runner
from remote_runner import Pool, LocalPbsWorker, Task

remote_runner.log_to(".remote-runnner.log", level="DEBUG")

workers = [
    LocalWorker()
]

tasks = [
    Task.load(Path("B0/state.dill"))
]

Pool(workers).run(tasks)
