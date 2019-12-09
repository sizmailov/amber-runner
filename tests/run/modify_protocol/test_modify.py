from remote_runner.utility import ChangeDirectory
from pathlib import Path
import subprocess
import shutil


def read_file(path: Path):
    with path.open() as f:
        return f.read()


def test_mod_and_run():
    with ChangeDirectory(Path(__file__).parent):
        wd = Path("P0")

        if wd.is_dir():
            shutil.rmtree(wd)

        subprocess.check_call(["coverage", "run", "-p", "./init.py"])
        assert (wd / "state.dill").is_file()

        subprocess.check_call(["coverage", "run", "-p", "./run.py"])
        assert int(read_file(wd / "exit_code")) == 0
        assert read_file(wd / "stdout").strip() == "Hello!"

        subprocess.check_call(["coverage", "run", "-p", "./modify_0.py"])
        subprocess.check_call(["coverage", "run", "-p", "./run.py"])
        assert int(read_file(wd / "exit_code")) == 0
        assert read_file(wd / "stdout").strip() == "World!"

        subprocess.check_call(["coverage", "run", "-p", "./modify_1.py"])
        subprocess.check_call(["coverage", "run", "-p", "./run.py"])
        assert int(read_file(wd / "exit_code")) == 0
        assert read_file(wd / "stdout").strip() == "FooBar"

        assert len([f for f in wd.glob("*") if f.is_dir()]) == 1
