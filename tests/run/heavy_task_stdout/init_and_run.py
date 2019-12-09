from amber_runner.MD import Step, MdProtocol
from pathlib import Path
from remote_runner import Pool, LocalWorker
from remote_runner.utility import ChangeToTemporaryDirectory


class HeavyStdoutOutput(Step):

    def run(self, md: 'MdProtocol'):
        for i in range(64 * 1024):
            print("-" * 256)


class MyMdProtocol(MdProtocol):
    def __init__(self, name: str):
        wd = Path(name)
        wd.mkdir(mode=0o755, exist_ok=True)
        MdProtocol.__init__(self, name, wd)
        self.greet = HeavyStdoutOutput("greet")


with ChangeToTemporaryDirectory():
    # with ChangeDirectory(Path(__file__).parent / "TMP"):
    Pool([LocalWorker()]).run([MyMdProtocol("./")])
    with open("stdout") as f:
        assert f.read().count("-") == 64 * 1024 * 256
