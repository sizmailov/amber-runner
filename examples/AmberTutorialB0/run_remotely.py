from pathlib import Path
import remote_runner
from remote_runner import Pool, SyncSSHWorker, Task

remote_runner.log_to(".remote-runnner.log", level="DEBUG")

workers = [
    SyncSSHWorker(
        host="bionmr",  # name of host from .ssh/config
        remote_user_rc=f"""
unset PYTHONPATH
source ~/venv-3.8/bin/activate
""",
        sync_period=600  # copy data back every 5 minutes
    )
]

tasks = [
    Task.load(Path("B0/state.dill"))
]

Pool(workers).run(tasks)
