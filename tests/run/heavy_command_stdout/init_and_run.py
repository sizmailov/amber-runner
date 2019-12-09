from amber_runner.command import Command, StringArgument
from amber_runner.MD import Step, MdProtocol
from pathlib import Path
from remote_runner import Pool, LocalWorker
from remote_runner.utility import ChangeToTemporaryDirectory


class MyCommand(Command):
    executable = ['python']

    def __init__(self, count, line):
        super(MyCommand, self).__init__()
        self.script = StringArgument('-c', f'for i in range({count}): print("{line}")')


class HeavyStdoutOutput(Step):

    def run(self, md: 'MdProtocol'):
        cmd = MyCommand(64*1024, "#" * 256)
        cmd.run()


class MyMdProtocol(MdProtocol):
    def __init__(self, name: str):
        wd = Path(name)
        wd.mkdir(mode=0o755, exist_ok=True)
        MdProtocol.__init__(self, name, wd)
        self.greet = HeavyStdoutOutput("greet")


with ChangeToTemporaryDirectory():
    Pool([LocalWorker()]).run([MyMdProtocol("./")])
    with open("stdout") as f:
        assert f.read() == ""
