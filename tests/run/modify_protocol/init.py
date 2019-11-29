from amber_runner.MD import Step, MdProtocol
from pathlib import Path


class SayHello(Step):

    def run(self, md: 'MdProtocol'):
        print("Hello!")


class MyMdProtocol(MdProtocol):
    def __init__(self, name: str):
        wd = Path(name)
        wd.mkdir(mode=0o755, exist_ok=True)
        MdProtocol.__init__(self, name, wd)
        self.greet = SayHello("greet")


md = MyMdProtocol("P0")
md.save(Path(md.wd) / md.state_filename)
