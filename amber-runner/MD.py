from collections import defaultdict
import subprocess
import uuid
import json
import remote_runner
import os
import f90nml
from typing import List, Tuple, Union, TextIO, DefaultDict, Dict, Literal
from pathlib import Path

ResidueId = int
AtomId = int
RestraintAtomIdTuple = Union[Tuple[AtomId, AtomId],
                             Tuple[AtomId, AtomId, AtomId],
                             Tuple[AtomId, AtomId, AtomId, AtomId]]

GroupTreeType = Literal["M", "S", "B", "3", "E", "*"]


class Namelist(f90nml.namelist.Namelist):

    def __call__(self, *args, **kwargs):
        assert len(args) == 0, "args are disallowed"
        for k, v in kwargs.items():
            self[k] = v


class TleapInput:
    frame = "frame"

    def __init__(self, outdir="1_build"):
        self.commands: List[str] = []
        self.outdir = outdir

    @property
    def frame_basename(self):
        return os.path.join(self.outdir, self.frame)

    def add_command(self, command: str):
        self.commands.append(command)

    def write(self, filename):
        with open(filename, "w") as f:
            f.write("\n".join(self.commands))

    def bond(self, atom1, atom2):
        self.add_command(f"bond {self.frame}.{atom1.rName}.{atom1.aName} {self.frame}.{atom2.rName}.{atom2.aName}")

    def load_pdb(self, filename):
        self.add_command(f"{self.frame} = loadpdb {filename}")

    def solvate_oct(self, water_model, shell_thickness):
        self.add_command(f"solvateoct {self.frame} {water_model} {shell_thickness}")

    def add_ions(self, ion, target_charge=0):
        self.add_command(f"addions {self.frame} {ion} {target_charge}")

    def save_amber_params(self):
        self.add_command(
            f"saveamberparm {self.frame} {self.frame_basename}.prmtop {self.frame_basename}.inpcrd")

    def source(self, filename):
        self.add_command(f"source {filename}")

    def save_pdb(self, filename=None):
        if filename is None: filename = self.frame
        self.add_command(f"savepdb {self.frame_basename} {self.frame_basename}.pdb")


class ParmedScript:  # former AmberTopologyModificator
    def __init__(self):
        self._commands = []

    def add_command(self, command):
        self._commands.append(command)

    def set_angle(self, mask1, mask2, mask3, force_constant, equilibrium_angle):
        self.add_command(f"setAngle {mask1} {mask2} {mask3} {force_constant:f} {equilibrium_angle:f}")

    def set_bond(self, mask1, mask2, force_constant, equilibrium_angle):
        self.add_command(f"setBond {mask1} {mask2} {force_constant:f} {equilibrium_angle:f}")

    def change_LJ_pair(self, mask1, mask2, radius, well_depth):
        self.add_command(f"changeLJpair {mask1} {mask2} {radius:f} {well_depth:f}")

    def delete_dihedral(self, mask1, mask2, mask3, mask4):
        self.add_command(f"deleteDihedral {mask1} {mask2} {mask3} {mask4}")

    def save(self, output_name):
        self.add_command(f"outparm {output_name}.prmtop")

    @property
    def commands(self):
        return self._commands
    #
    # @staticmethod
    # def run_command(prmtop, command):
    #     amberhome = os.environ.get("AMBERHOME", None)
    #     parmed_path = ("" if amberhome is None else amberhome) + "parmed.py"
    #     parmed = subprocess.Popen(["python2.7", parmed_path, prmtop])
    #     o, e = parmed.communicate(input=command)
    #     return o, e


class FlatWelledParabola:

    def __init__(self, r1: float, r2: float, r3: float, r4: float, k2: float, k3: float):
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3
        self.r4 = r4
        self.k2 = k2
        self.k3 = k3


class AmberNMRRestraints(Dict[RestraintAtomIdTuple, List[FlatWelledParabola]]):

    def add(self, atoms: RestraintAtomIdTuple, penalty: FlatWelledParabola):
        if atoms not in self:
            self[atoms] = [penalty]
        else:
            self[atoms].append(penalty)

    def distance(self, id1: AtomId, id2: AtomId, penalty: FlatWelledParabola):
        atoms = min(id1, id2), max(id1, id2)
        self.add(atoms, penalty)

    def angle(self, id1: AtomId, id2: AtomId, id3: AtomId, penalty: FlatWelledParabola):
        atoms = min(id1, id3), id2, max(id1, id3)
        self.add(atoms, penalty)

    def dihedral(self, id1: AtomId, id2: AtomId, id3: AtomId, id4: AtomId, penalty: FlatWelledParabola):
        atoms = (id1, id2, id3, id4) if id2 < id3 else (id4, id3, id2, id1)
        self.add(atoms, penalty)

    def del_distance(self, id1: AtomId, id2: AtomId):
        atoms = min(id1, id2), max(id1, id2)
        x = self.pop(atoms, [])
        return len(x)

    def del_angle(self, id1: AtomId, id2: AtomId, id3: AtomId):
        atoms = min(id1, id3), id2, max(id1, id3)
        x = self.pop(atoms, [])
        return len(x)

    def del_dihedral(self, id1: AtomId, id2: AtomId, id3: AtomId, id4: AtomId):
        atoms = (id1, id2, id3, id4) if id2 < id3 else (id4, id3, id2, id1)
        x = self.pop(atoms, [])
        return len(x)

    def write(self, fout: TextIO):
        for ats, penalties in self.items():
            cs_ats = ','.join(map(str, ats))
            for penalty in penalties:
                fout.write(f"""
&rst  ! 
     iat={cs_ats}, r1={penalty.r1}, r2={penalty.r2}, r3={penalty.r3}, r4={penalty.r4},
     rk2={penalty.k2}, rk3={penalty.k3}
&d
""")


class VaryingConditions:
    def __init__(self):
        self.wts: List[Dict] = []

    def add(self, **kwargs):
        assert "type" in kwargs
        assert kwargs["type"] != "END", 'Redundant wt namelist type=END. It\' is added automatically'
        self.wts.append(Namelist(**kwargs))

    def write(self, out: TextIO):
        if len(self.wts) > 0:
            Namelist(wt=self.wts + [{"type": "END"}]).write(out)


class GroupSelectionFind:
    def __init__(self, atom_name="*", atom_type="*", tree_type: GroupTreeType = "*", residue_name="*"):
        self.atom_name = atom_name
        self.atom_type = atom_type
        self.atom_tree = tree_type
        self.residue_name = residue_name

    def __str__(self):
        return f"{self.atom_name} {self.atom_type} {self.atom_tree} {self.residue_name}"


class GroupSelection:
    def __init__(self,
                 title,
                 weight=None,
                 find: List[GroupSelectionFind] = None,
                 atom_id_ranges: List[Tuple[AtomId, AtomId]] = None,
                 residue_id_ranges: List[Tuple[ResidueId, ResidueId]] = None):
        assert any([weight, find, atom_id_ranges, residue_id_ranges]), "At least one attribute should be not None"
        if find is None:
            find = []
        if atom_id_ranges is None:
            atom_id_ranges = []
        if residue_id_ranges is None:
            residue_id_ranges = []

        self.title = title
        self.weight = weight
        self.find = find
        self.atom_id_ranges = atom_id_ranges
        self.residue_id_ranges = residue_id_ranges

    def write(self, out: TextIO):
        out.write(f"{self.title}\n")
        if self.weight is not None:
            out.write(f"{self.weight}\n")
        if len(self.find) > 0:
            out.write("FIND\n")
            for find in self.find:
                out.write(f"{find}\n")
            out.write("SEARCH\n")
        for first, last in self.atom_id_ranges:
            out.write(f"ATOM {first} {last}\n")
        for first, last in self.atom_id_ranges:
            out.write(f"ATOM {first} {last}\n")
        out.write("END\n")


class GroupSelections(List[GroupSelection]):

    def write(self, out: TextIO):
        if len(self) > 0:
            for group_selection in self:
                group_selection.write(out)
            out.write("END\n")


class FileRedirections(Dict[str, str]):
    allowed_types = [
        "LISTIN",
        "LISTOUT",
        "DISANG",
        "NOESY",
        "SHIFTS",
        "PCSHIFT",
        "DIPOLE",
        "CSA",
        "DUMPAVE"
    ]

    TypesLiteral = Literal[
        "LISTIN",
        "LISTOUT",
        "DISANG",
        "NOESY",
        "SHIFTS",
        "PCSHIFT",
        "DIPOLE",
        "CSA",
        "DUMPAVE"
    ]

    def __setitem__(self, key, value):
        assert key in self.allowed_types
        super().__setitem__(key, value)

    def write(self, out: TextIO):
        for key, value in self.items():
            out.write(f"{key}={value}\n")


class AmberInput:

    def __init__(self):
        self.namelist = Namelist()
        self.varying_conditions = VaryingConditions()
        self.restraints = AmberNMRRestraints()
        self.group_selections = GroupSelections()
        self.file_redirections = FileRedirections()

    def pin(self, group_selection: GroupSelection):
        self.group_selections.append(group_selection)

    def redirect(self, file_type: FileRedirections.TypesLiteral, filename: str):
        self.file_redirections[file_type] = filename

    def write(self, out: TextIO):
        title = "Generated by amber-runner"

        if len(self.restraints) > 0:
            self.cntrl["nmropt"] = 1
        else:
            self.cntrl["nmropt"] = 0

        out.write(f"{title}\n")
        self.namelist.write(out)
        self.varying_conditions.write(out)
        self.file_redirections.write(out)
        self.group_selections.write(out)

    @property
    def cntrl(self) -> Namelist:
        return self.namelist["cntrl"]

    @property
    def ewald(self) -> Namelist:
        return self.namelist["ewald"]

    @property
    def qmmm(self) -> Namelist:
        return self.namelist["qmmm"]

    @property
    def pb(self) -> Namelist:
        return self.namelist["pb"]

    @property
    def amoeba(self) -> Namelist:
        return self.namelist["amoeba"]

    @property
    def debugf(self) -> Namelist:
        return self.namelist["debugf"]

    @property
    def emap(self) -> Namelist:
        return self.namelist["emap"]


class MD(remote_runner.Task):

    def __init__(self, name: str, wd: Path):
        super().__init__(wd=wd)
        self.name = name

        self.tleaprc = TleapInput()
        self.parmed = ParmedScript()

        self.min1_parameters = AmberInput()
        self.min2_parameters = AmberInput()
        self.heat_parameters = AmberInput()
        self.equil_parameters = AmberInput()
        self.run_parameters = AmberInput()

        self.reference = None
        self.restart = None
        self.prmtop = None

        self.pmemd_executable = ["pmemd"]

        self.current_step = 0

        self.setup_is_done = False

    def build(self):
        self.mkdir_p("1_build")
        self.run_tleap()
        self.run_parmed()

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

    def call_cmd(self, cmd, **kwargs):
        """ Returns tuple (exit_code, command_output) """

        self.log("Running " + cmd[0] + "...", MD.TRACE)
        self.log("with parameters`" + " ".join(cmd[1:]) + "`...", MD.DEBUG)
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

    def call_pmemd(self, prefix):
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
        self._restart_filename = prefix + ".rst"

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

    def get_type_of(self, mask):
        import StringIO, sys
        output = StringIO.StringIO("")

        from ParmedTools.parmed_cmd import ParmedCmd
        from ParmedTools.parmlist import ParmList
        from ParmedTools.exceptions import (ParmError, InterpreterError)

        amber_prmtop = ParmList()
        amber_prmtop.add_parm(self.tleaprc.output_name + ".mod.prmtop")

        command = StringIO.StringIO("printLJTypes " + mask)

        parmed_commands = ParmedCmd(amber_prmtop, stdin=command, stdout=output)
        parmed_commands.use_rawinput = 0
        # parmed_commands.interpreter = opt.interpreter
        parmed_commands.prompt = ''
        # Loop through all of the commands
        try:
            parmed_commands.cmdloop()
        except InterpreterError as err:
            sys.exit('%s: %s' % (type(err).__name__, err))
        except ParmError:
            # This has already been caught and printed. If it was re-raised, then
            # that means we wanted to exit
            sys.exit(1)

        # DANGEROUS PARSING  ^_^
        lines = output.getvalue().split("\n")
        import re
        return int(re.split("\s+", lines[3].strip())[-1])
