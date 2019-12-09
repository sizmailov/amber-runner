from collections import OrderedDict
from typing import Generic, TypeVar
from pathlib import Path

import remote_runner
from remote_runner.utility import ChangeDirectory

from .executables import PmemdCommand, SanderCommand, TleapCommand
from .inputs import AmberInput, TleapInput

CommandType = TypeVar('CommandType')
InputType = TypeVar("InputType")


class Step:
    step_dir: Path

    def __init__(self, name):
        self.name = name
        self.is_complete = False

    def run(self, md: 'MdProtocol'):
        raise NotImplementedError()


class CommandWithInput(Generic[CommandType, InputType]):
    def __init__(self, exe: CommandType, inp: InputType):
        self.exe = exe
        self.input = inp

    def run(self, **kwargs):
        input_filename = Path(self.exe.input)
        with input_filename.open("w") as inp:
            self.input.write(inp)
        return self.exe.run(**kwargs)


class Build(Step):
    def __init__(self, name):
        super().__init__(name)
        self.tleap = CommandWithInput(exe=TleapCommand(), inp=TleapInput())
        # self.parmed = CommandWithInput(exe=ParmedCommand(), inp=ParmedInput())

    def run(self, md: 'MdProtocol'):
        self.tleap.input.output_dir = self.step_dir
        self.tleap.exe.input = self.step_dir / 'tleap.in'
        self.tleap.run()

        frame_prmtop = self.step_dir / f"{self.tleap.input.frame}.prmtop"
        assert frame_prmtop.exists()
        md.sander.prmtop = frame_prmtop

        frame_incrd = self.step_dir / f"{self.tleap.input.frame}.rst7"  # tleap always produces ascii restart
        assert frame_incrd.exists()
        md.sander.inpcrd = frame_incrd


class SingleSanderCall(Step):
    def __init__(self, name):
        super().__init__(name)
        self.input = AmberInput()

    def run(self, md: 'MdProtocol'):
        with md.sander.scope_args(output_prefix=str(self.step_dir / self.name)) as exe:
            CommandWithInput(exe, self.input).run()
            md.sander.inpcrd = md.sander.restrt


class RepeatedSanderCall(Step):
    def __init__(self, name: str, number_of_steps: int):
        self.current_step = 0
        self.number_of_steps = number_of_steps
        self.input = AmberInput()
        super().__init__(name)

    def run(self, md: 'MdProtocol'):
        while self.current_step < self.number_of_steps:
            self.before_call(md)
            with md.sander.scope_args(output_prefix=str(self.step_dir / f"{self.name}{self.current_step:05d}")) as exe:
                CommandWithInput(exe, self.input).run()
                md.sander.inpcrd = md.sander.restrt
            self.after_call(md)
            self.current_step += 1
            md.checkpoint()

    def before_call(self, md: 'MdProtocol'):
        pass

    def after_call(self, md: 'MdProtocol'):
        pass

    @property
    def is_complete(self):
        return self.current_step >= self.number_of_steps

    @is_complete.setter
    def is_complete(self, value: bool):
        assert (self.current_step >= self.number_of_steps) == value


class MdProtocol(remote_runner.Task):
    _protected_methods = remote_runner.Task._protected_methods + ["checkpoint"]
    sander: SanderCommand = PmemdCommand()

    def __init__(self, name: str, wd: Path):
        super().__init__(wd=wd)
        self.name = name
        self.__steps = OrderedDict()

    @staticmethod
    def mkdir(path: Path, mode=0o755):
        path.mkdir(mode=mode, exist_ok=True)
        return path

    def __setattr__(self, key, value):
        if isinstance(value, Step):
            self.__steps[key] = value
            value.step_dir = Path(f"{len(self.__steps) - 1}_{value.name}")
        super().__setattr__(key, value)

    # @final
    def run(self):
        for i, step in enumerate(self.__steps.values()):
            if step.is_complete:
                continue
            with ChangeDirectory():
                self.mkdir(step.step_dir)
                step.run(self)
                step.is_complete = True
                self.checkpoint()

    def checkpoint(self):
        self.save(self.state_filename)
