from pathlib import Path
import remote_runner
from remote_runner import Pool, SSHPbsWorker, Task

remote_runner.log_to(".remote-runnner.log", level="DEBUG")

workers = [
    SSHPbsWorker(
        host="bionmr",  # name of host from .ssh/config
        remote_user_rc=f"""
unset PYTHONPATH
source ~/venv-3.8/bin/activate
""",
        resources="nodes=1:ppn=1:gpus=1,walltime=1:00:00"
    )
]

tasks = [
    Task.load(Path("B0/state.dill"))
]

Pool(workers).run(tasks)
