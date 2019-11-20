import os
from pathlib import Path
from typing import List, final
import remote_runner
from .command import Command
from .inputs import InputWriter, AmberInput, TleapInput, ParmedInput
from .executables import PmemdCommand, SanderCommand, ParmedCommand, TleapCommand
from remote_runner.utility import ChangeDirectory


class Step:
    def __init__(self, name):
        self.name = name
        self.is_complete = False

    def run(self, md: 'MD', step_dir: Path):
        raise NotImplementedError()


class CommandWithInput:
    def __init__(self, exe: Command, inp: InputWriter):
        self.exe = exe
        self.input = inp

    def run(self, input_filename: Path, **kwargs):
        with input_filename.open("w") as inp:
            self.input.write(inp)
        return self.exe.run(**kwargs)


class Build(Step):
    def __init__(self, name):
        super().__init__(name)
        self.tleap = CommandWithInput(exe=TleapCommand(), inp=TleapInput())
        # self.parmed = CommandWithInput(exe=ParmedCommand(), inp=ParmedInput())

    def run(self, md: 'MD', step_dir: Path):
        self.tleap.run(step_dir / "tleap.in")
        # self.parmed.run(step_dir / "parmed.in")
        md.sander.restrt = step_dir / "frame.prmtop"


class SingleSanderCall(Step):
    def __init__(self, name):
        super().__init__(name)
        self.input = AmberInput()

    def run(self, md: 'MD', step_dir: Path):
        with md.sander.scope_args(output_prefix=str(step_dir / self.name)) as exe:
            exe.run(self.input, step_dir / f"{self.name}.in")


class RepeatedSanderCall(Step):
    def __init__(self, name, number_of_steps: int):
        super().__init__(name)
        self.input = AmberInput()
        self.current_step = 0
        self.number_of_steps = number_of_steps

    def run(self, md: 'MD', step_dir: Path):
        while self.current_step < self.number_of_steps:
            with md.sander.scope_args(output_prefix=str(step_dir / f"{self.name}{self.current_step:05d}")) as exe:
                exe.run(self.input, step_dir / f"{self.name}{self.current_step:05d}.in")
            self.current_step += 1
            md.checkpoint()


class MdProtocol(remote_runner.Task):

    def __init__(self, name: str, wd: Path):
        super().__init__(wd=wd)
        self.name = name
        self.sander: SanderCommand = PmemdCommand()

    @staticmethod
    def mkdir_p(path):
        if not os.path.isdir(path):
            os.mkdir(path)

    @property
    def steps(self) -> List[Step]:
        raise NotImplementedError()

    @final
    def run(self):
        for i, step in enumerate(self.steps):
            with ChangeDirectory():
                wd = f"{1 + i}_{step.name}"
                self.mkdir_p(wd)
                step.run(self, Path(wd))
                self.checkpoint()

    def checkpoint(self):
        self.save(self.state_filename)

