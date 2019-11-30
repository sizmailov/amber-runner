from .command import Command, OptionalStringArgument, OptionalBooleanArgument, LambdaStringArgument, \
    OptionalListArgument
from typing import List


class SanderCommand(Command):
    executable: List[str] = ["sander"]  # must contain `mpirun -np N` part (if any) as well

    def __init__(self):
        super().__init__()
        self.output_prefix = "run"  # todo: change it

        self.input = self.mdin = LambdaStringArgument("-i", lambda: f"{self.output_prefix}.in")
        self.mdout = LambdaStringArgument("-o", lambda: f"{self.output_prefix}.out")
        self.restrt = LambdaStringArgument("-r", lambda: f"{self.output_prefix}.{self.restrt_extension}")
        self.prmtop = OptionalStringArgument("-p")
        self.inpcrd = OptionalStringArgument("-c")

        self.mdinfo = OptionalStringArgument("-inf")
        self.refc = OptionalStringArgument("-ref")
        self.mtmd = OptionalStringArgument("-mtmd")
        self.mdcrd = LambdaStringArgument("-x", lambda: f"{self.output_prefix}.nc")
        self.inptraj = OptionalStringArgument("-y")
        self.mdvel = OptionalStringArgument("-v")
        self.mdfrc = OptionalStringArgument("-frc")
        self.radii = OptionalStringArgument("-radii")
        self.mden = OptionalStringArgument("-e")
        self.cpin = OptionalStringArgument("-cpin")
        self.cprestrt = OptionalStringArgument("-cprestrt")
        self.cpout = OptionalStringArgument("-cpout")
        self.cein = OptionalStringArgument("-cein")
        self.cerestrt = OptionalStringArgument("-cerestrt")
        self.ceout = OptionalStringArgument("-ceout")
        self.evbin = OptionalStringArgument("-evbin")
        self.suffix = OptionalStringArgument("-suffix")

        self.override = OptionalBooleanArgument("-O", True)
        self.append = OptionalBooleanArgument("-A", False)

    @property
    def restrt_extension(self) -> str:
        from pathlib import Path
        import f90nml
        if Path(self.input).is_file():
            try:
                with open(self.input) as file:
                    inp = f90nml.reads(file)
                    if inp.cntrl["ioutfm"] == 0:
                        return "rst7"  # plain ascii restart
            except AttributeError:
                pass
        return "ncrst"  # binary restart


class PmemdCommand(SanderCommand):
    executable: List[str] = ["pmemd"]  # must contain `mpirun -np N` part (if any) as well

    def __init__(self):
        super(PmemdCommand, self).__init__()

        self.logfile = OptionalStringArgument("-l")
        self.process_map_file = OptionalStringArgument("-gpes")
        self.allow_small_box = OptionalBooleanArgument("-AllowSmallBox")


class TleapCommand(Command):
    executable = ["tleap"]

    def __init__(self):
        super().__init__()
        self.include_dirs = OptionalListArgument("-I")
        self.ignore_startup = OptionalBooleanArgument("-s", True)
        self.input = OptionalStringArgument("-f")


class ParmedCommand(Command):
    executable = ["parmed"]

    def __init__(self):
        super().__init__()

        self.no_splash = OptionalBooleanArgument("--no-splash")
        self.override = OptionalBooleanArgument("--override")
        self.input = OptionalStringArgument("--input")
        self.log_file = OptionalStringArgument("--logfile")
