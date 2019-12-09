from remote_runner.utility import ChangeDirectory
from pathlib import Path
import subprocess


def test_mod_and_run():
    with ChangeDirectory(Path(__file__).parent):
        assert subprocess.check_output(["coverage", "run", "-p", "./init_and_run.py"]).count(b"#") == 64 * 1024 * 256
