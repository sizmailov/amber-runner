from .command import Command, ArgumentFactory
from typing import List


class SanderCommand(Command):
    executable: List[str] = ["pmemd"]  # must contain `mpirun -np N` part (if any) as well

    def __init__(self):
        super().__init__()
        arg_factory = ArgumentFactory(self)
        self.output_prefix = "run"  # todo: change it

        self.mdin = arg_factory.lambda_string("-i", lambda: f"{self.output_prefix}.in")
        self.mdout = arg_factory.lambda_string("-o", lambda: f"{self.output_prefix}.out")
        self.restrt = arg_factory.lambda_string("-r", lambda: f"{self.output_prefix}.rst")
        self.prmtop = arg_factory.string("-p", None)
        self.inpcrd = arg_factory.string("-c", None)

        self.mdinfo = arg_factory.string("-inf")
        self.refc = arg_factory.string("-ref")
        self.mtmd = arg_factory.string("-mtmd")
        self.mdcrd = arg_factory.string("-x")
        self.inptraj = arg_factory.string("-y")
        self.mdvel = arg_factory.string("-v")
        self.mdfrc = arg_factory.string("-frc")
        self.radii = arg_factory.string("-radii")
        self.mden = arg_factory.string("-e")
        self.cpin = arg_factory.string("-cpin")
        self.cprestrt = arg_factory.string("-cprestrt")
        self.cpout = arg_factory.string("-cpout")
        self.cein = arg_factory.string("-cein")
        self.cerestrt = arg_factory.string("-cerestrt")
        self.ceout = arg_factory.string("-ceout")
        self.evbin = arg_factory.string("-evbin")
        self.suffix = arg_factory.string("-suffix")

        self.override = arg_factory.boolean("-O", True)
        self.append = arg_factory.boolean("-A", False)


class PmemdCommand(SanderCommand):
    def __init__(self):
        super(PmemdCommand, self).__init__()
        arg_factoty = ArgumentFactory(self)

        self.logfile = arg_factoty.string("-l")
        self.process_map_file = arg_factoty.string("-gpes")


class TleapCommand(Command):
    executable = ["tleap"]

    def __init__(self):
        super().__init__()
        arg_factory = ArgumentFactory(self)
        self.include_dirs = arg_factory.list("-I")
        self.ignore_startup = arg_factory.boolean("-s")
        self.source = arg_factory.string("-f")


class ParmedCommand(Command):
    executable = ["parmed"]
    no_splash: bool = True
    override: bool = True
    script_filename: str = None

    def __init__(self):
        super().__init__()
        arg_factory = ArgumentFactory(self)

        self.no_splash = arg_factory.boolean("--no-splash")
        self.override = arg_factory.boolean("--override")
        self.input = arg_factory.string("--input")
        self.log_file = arg_factory.boolean("--logfile")
