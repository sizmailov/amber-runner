import os
import subprocess
from pathlib import Path

import remote_runner


class Step:
    def __init__(self, name):
        self.name = name

    def run(self, md: 'MD', step_dir: Path):
        raise NotImplementedError()


class CommandWithInput:
    def __init__(self, exe: Command, inp: InputWriter):
        self.exe = exe
        self.input = inp

    def run(self, input_filename: Path, **kwargs):
        return self.exe.run(inp=self.input, input_filename=input_filename, **kwargs)


class Build(Step):
    def __init__(self, name):
        super().__init__(name)
        self.tleap = CommandWithInput(exe=TleapCommand(), inp=TleapInput())
        self.parmed = CommandWithInput(exe=ParmedCommand(), inp=ParmedInput())

    def run(self, md: 'MD', step_dir: Path):
        self.tleap.run(step_dir / "tleap.in")
        self.parmed.run(step_dir / "parmed.in")
        md.exe.previous_rst = 1


class Minimize(Step):
    def __init__(self, name):
        super().__init__(name)
        self.min_1_input = AmberInput()
        self.min_2_input = AmberInput()

    def run(self, md: 'MD', step_dir: Path):
        md.exe(output=str(step_dir / "min_1")).run(self.min_1_input, step_dir / "min_1.in")
        md.exe.run(self.min_2_input, step_dir / "min_2.in")


class Equilibrate(Step):
    pass


class ProductionRun(Step):
    pass


class MD(remote_runner.Task):

    def __init__(self, name: str, wd: Path):
        super().__init__(wd=wd)
        self.name = name

        self.exe: SanderCommand = PmemdCommand()

        self.min1 = AmberInput()
        self.min2 = AmberInput()
        self.heat = AmberInput()
        self.equil = AmberInput()
        self.run = AmberInput()

        self.reference = None
        self.restart = None
        self.prmtop = None

    def mkdir_p(self, path):
        if not os.path.isdir(path):
            self.log("mkdir %s" % path)
            os.mkdir(path)

    def minimize(self):
        self.mkdir_p(MD._min_dir)

        self.min1_parameters.write_to(MD._min_dir + "/min_1")
        self.call_pmemd(MD._min_dir + "/min_1")

        self.min2_parameters.write_to(MD._min_dir + "/min_2")
        self.call_pmemd(MD._min_dir + "/min_2")

    def heat(self):
        self.mkdir_p(MD._heat_dir)
        self.heat_parameters.write_to(MD._heat_dir + "/heat")
        self.call_pmemd(MD._heat_dir + "/heat")

    def equilibrate(self):
        self.mkdir_p(MD._equilibration_dir)
        self.equil_parameters.write_to(MD._equilibration_dir + "/equil")
        self.call_pmemd(MD._equilibration_dir + "/equil")

    @property
    def required_steps(self):
        if self.current_step > 0:
            return [self.current_step - 1]
        else:
            return []

    def do_md_step(self):
        next_step = self.current_step + 1
        self.mkdir_p(MD._run_dir)

        step_prefix = self._run_dir + "/run" + MD._pattern % next_step
        self.run_parameters.write_to(step_prefix)
        self.call_pmemd(step_prefix)

        self.current_step = next_step
        self.save()

    def run_setup(self):
        raise NotImplementedError()

    def run_continue(self):
        raise NotImplementedError()

    def run(self):
        if not self.setup_is_done:
            self.run_setup()
        self.run_continue()

    def call_cmd(self, cmd):
        output = None
        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            self.log("Process " + " ".join(cmd) + " returned non zero status " + str(e.returncode) + "."
                                                                                                     "with message" + e.message,
                     MD.ERROR)
            if abort_on_failure:
                self.log("Output: " + e.output, MD.FATAL)
            else:
                return e.returncode, e.output
        except Exception as e:
            self.log("Unspecified failure " + e.message + "on command " + " ".join(cmd) + ". Abort.", MD.FATAL)

        # 0 -- success code
        return 0, output

    def call_cmd_pipe(self, cmd, stdin):
        import subprocess
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            o, e = proc.communicate(stdin)
        except subprocess.CalledProcessError as e:
            self.log("Process " + " ".join(cmd) + " returned non zero status " + str(e.returncode) + "."
                                                                                                     "with message" + e.message,
                     MD.ERROR)
            self.log("Output: " + e.output, MD.FATAL)
        except Exception as e:
            self.log("Unspecified failure " + e.message + "on command " + " ".join(cmd) + ". Abort.", MD.FATAL)

        return 0, o

    def run_pmemd(self):
        cmd = self.pmemd_executable + [
            "-O",
            "-i", prefix + ".in",
            "-o", prefix + ".out",
            "-p", self.prmtop,
            "-c", self.restart,
            "-ref", self.reference,
            "-x", prefix + ".nc",
            "-r", prefix + ".rst",
            "-inf", prefix + ".mdinfo",
            "-l", prefix + ".log"
        ]
        self.call_cmd(cmd)

    def _on_fatal(self):
        import sys
        self.check_wd()
        self.save_state("fatal_state.pickle")
        sys.exit(1)

    def set_step_as_restart_file(self, step_number=-1):
        """
        :param step_number:
        :type step_number: int
        :return:
        """
        if step_number < 0:
            step_number = self.current_step + step_number + 1

        self._restart_filename = MD._run_dir + "/" + "run" + MD._pattern % step_number + ".rst"
