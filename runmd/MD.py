
from collections import defaultdict
import subprocess
import os

from pyxmol.base import *
from pyxmol.predicate import *


class TleapInput(object):   #  former AmberTleapRc

    default_box = "wbox"

    def __init__(self):
        self._commands = []
        self.output_name = None
        self.pdb_output_name = None

    def add_command(self, command):
        self._commands.append(command)

    def get_commands(self):
        return self._commands

    def write_commands_to(self, filename):
        with open(filename,"w") as f:
            f.write("\n".join(self.get_commands()))

    def add_ss_bonds(self, ss_bonded_resid_pairs):
        for bond in ss_bonded_resid_pairs:
            self.add_command("bond wbox."+str(bond[0])+".SG wbox."+str(bond[1])+".SG")

    def load_pdb(self, pdbfilename, box=default_box):
        self.add_command("%s = loadpdb %s" % (box, pdbfilename))

    def solvate_oct(self, water_model, shell_thickness, box=default_box):
        self.add_command("solvateoct %s %s %f" % (box, water_model, shell_thickness))

    def add_ions(self, ion, target_charge=0, box=default_box):
        self.add_command("addions %s %s %f"%(box,ion,target_charge))

    def save_params(self, box=default_box, output_name=None):
        if output_name is None: output_name = box
        self.output_name = output_name
        self.add_command("saveamberparm %s %s.prmtop %s.inpcrd" % (box, output_name, output_name))

    def source(self, filename):
        self.add_command("source %s" % filename )

    def save_pdb(self, box=default_box, output_name=None):
        if output_name is None: output_name = box
        self.pdb_output_name = output_name
        self.add_command("savepdb %s %s.pdb" % (box, output_name) )

class ParmedScript(object):  # former AmberTopologyModificator
    def __init__(self):
        self._commands = []

    def add_command(self, command):
        self._commands.append(command)

    def set_angle(self, mask1, mask2, mask3, force_constant, equilibrium_angle):
        self.add_command("setAngle %s %s %s %f %f" % (
            mask1,
            mask2,
            mask3,
            force_constant,
            equilibrium_angle))

    def set_bond(self, mask1, mask2, force_constant, equilibrium_angle):
        self.add_command("setBond %s %s %f %f" % (
            mask1,
            mask2,
            force_constant,
            equilibrium_angle))

    def set_vdw(self, mask1, mask2, radius, well_depth):
        self.add_command("changeLJpair %s %s %f %f" % (mask1, mask2, radius, well_depth))

    def del_dihedral(self, mask1, mask2, mask3, mask4):
        self.add_command("deleteDihedral %s %s %s %s" % (mask1, mask2, mask3, mask4))

    def save_as(self, output_name):
        self.add_command("outparm %s.prmtop" % output_name)

    def get_commands(self):
        return self._commands

    @staticmethod
    def run_command(self, prmtop, command):
        import subprocess
        import os
        amberhome = os.environ.get("AMBERHOME", None)
        parmed_path  = ("" if amberhome is None else amberhome )+ "parmed.py"
        parmed = subprocess.Popen(["python2.7", parmed_path, prmtop])
        o, e = parmed.communicate(input=command)
        return o, e

class AmberInput(object):  # former AmberInputFile

    def __init__(self):
        self._parameters = {}
        self._noe_restraints = defaultdict(list)
        self._pinned = []

    def set(self, **kwargs):
        for k,v in kwargs.iteritems():
            self[k] = v
        return self

    def __setitem__(self, key, value):
        self._parameters[key] = value
        return self

    def __getitem__(self, key):
        return self._parameters[key]

    def _add_noe_restraint(self, atoms, r1, r2, r3, r4, k2, k3, comment):
        atoms_str = ",".join(map(lambda aid: "%d"%aid, atoms))
        noe = """
&rst  ! {comment}
  ixpk= 0, nxpk= 0, iat={atoms_str}, r1={r1}, r2={r2}, r3={r3}, r4={r4},
      rk2={k2}, rk3={k3}, ir6=1, ialtd=0,
&end
""" .format(**locals())
        self._noe_restraints[atoms].append(noe)

    def add_distance_restraint(self, aId1, aId2, r1, r2, r3, r4, k2, k3, comment=""):
        atoms = min(aId1,aId2), max(aId1, aId2)
        self._add_noe_restraint(
                        atoms,
                        r1, r2, r3, r4,
                        k2, k3, comment)

    def add_angle_restraint(self, aId1, aId2, aId3, r1, r2, r3, r4, k2, k3, comment=""):
        atoms = min(aId1, aId3), aId2, max(aId1, aId3)
        self._add_noe_restraint(
            atoms,
            r1, r2, r3, r4,
            k2, k3, comment)

    def set_dihedral_restraint(self, aId1, aId2, aId3, aId4, r1, r2, r3, r4, k2, k3, comment=""):
        atoms = (aId1, aId2, aId3, aId4) if aId2 < aId3 else (aId4, aId3, aId2, aId1)
        self._add_noe_restraint(
            atoms,
            r1, r2, r3, r4,
            k2, k3, comment)

    def add_atom_pin(self, force_constant, filters, list_of_res_ranges):
        self._pinned.append((force_constant, filters, list_of_res_ranges))

    def del_atom_pins(self):
        self._pinned = []

    def del_distance_restraints(self, aId1, aId2):
        atoms = min(aId1, aId2), max(aId1, aId2)
        x = self._noe_restraints.pop(atoms,[])
        return len(x)

    def del_angle_restraint(self, aId1, aId2, aId3):
        atoms = min(aId1, aId3), aId2, max(aId1, aId3)
        x = self._noe_restraints.pop(atoms, [])
        return len(x)

    def del_dihedral_restraint(self, aId1, aId2, aId3, aId4):
        atoms = (aId1, aId2, aId3, aId4) if aId2 < aId3 else (aId4, aId3, aId2, aId1)
        x = self._noe_restraints.pop(atoms, [])
        return len(x)

    def get_input_script(self, restraints_filename=None):


        if len(self._noe_restraints)>0:
            self["nmropt"] = 1
        else:
            self["nmropt"] = 0

        params = (" &cntrl\n"
                  + ", \n".join([ "    {:<10} = {:<10}".format(key, value ) for key, value in self._parameters.iteritems() ])
                  + "\n/\n"
                  )
        pins = ""

        if len(self._pinned) > 0:
            for pin in self._pinned:
                force_constant, filters, rranges = pin
                pins += "Pinned residues with filter:\n"
                pins += "%lf\n" % force_constant
                if filters is not None: pins += "FIND\n" + "\n".join(filters) + "SEARCH\n"
                pins += "\n".join(["RES %d %d" % rr for rr in rranges])
            pins += "\nEND\n"

        noe_restr = ""

        wt = " &wt type='END' \n/\n"

        if len(self._noe_restraints) > 0:
            assert(restraints_filename is not None)
            noe_restr = "DISANG={restraints_filename}\nEND\n".format(**locals())

        return params + wt + noe_restr + pins +  "END"

    def get_restraints_script(self):
        if self._noe_restraints.__len__() == 0:
            return None
        import itertools
        return "\n".join(itertools.chain(*self._noe_restraints.values()))

    def write_to(self, prefix):
        with open(prefix+".in", "w") as f:
            f.write(self.get_input_script(prefix + ".restraints"))

        if len(self._noe_restraints) > 0:
            with open(prefix + ".restraints", "w") as f:
                f.write(self.get_restraints_script())


class MD(object):

    FATAL = -1
    ERROR = FATAL+1
    WARNING = ERROR+1
    INFO = WARNING+1
    TRACE = INFO+1
    DEBUG = TRACE+1

    __msg_level = {FATAL:   " FATAL ",
                   ERROR:   " ERROR ",
                   WARNING: "WARNING",
                   INFO:    " INFO  ",
                   TRACE:   " TRACE ",
                   DEBUG:   " DEBUG "}

    _build_dir = "1_build"
    _min_dir = "2_minimization"
    _heat_dir = "3_heat"
    _equilibration_dir = "4_equilibration"
    _run_dir = "5_run"
    _pattern = "%05d"
    _dump_filename = "auto_dump.pickle"
    _log_filename = "log.log"
    _box = "box"

    def __init__(self, name, trj_home_dir):
        self.trj_home = os.path.abspath(trj_home_dir)

        self._name = name

        self.tleaprc = TleapInput()
        self.parmed = ParmedScript()

        self.min1_parameters = AmberInput()
        self.min2_parameters = AmberInput()
        self.heat_parameters = AmberInput()
        self.equil_parameters = AmberInput()
        self.run_parameters = AmberInput()

        self._reference_filename = None
        self._restart_filename = None
        self._prmtop = None

        self._pmemd_executable = ["pmemd"]
        self.keep_restart = True
        self.keep_netcdf = True
        self.verbosity = MD.INFO
        self.tee_log_to_stdout = False

        self.current_step = 0

        self.mkdir_p(trj_home_dir)
        self.setup_is_done = False
        self.required_steps = []
        self.restricted_structure = None  # chains

        os.chdir(trj_home_dir)

    def build(self):
        import shutil
        self.log("Building parameters...")
        self.check_wd()
        self.mkdir_p(MD._build_dir)

        self.log("Writing tleap parameters...", MD.DEBUG)

        self.tleaprc.write_commands_to(MD._build_dir+"/tleap.rc")
        self.call_cmd(["tleap", "-s", "-f", MD._build_dir+"/tleap.rc" ])



        mod_top = self.tleaprc.output_name + ".mod.prmtop"
        if os.path.isfile(mod_top):
            shutil.move(mod_top, mod_top+"~")
        if len(self.parmed._commands)!=0:
            self.call_cmd_pipe(
                ["parmed.py", self.tleaprc.output_name+".prmtop"],
                "\n".join(
                    self.parmed.get_commands()
                    +["outparm %s "%(mod_top)]
                    +["quit"]
                )
            )
        else:
            shutil.copyfile(self.tleaprc.output_name+".prmtop", mod_top)
        self._restart_filename = self.tleaprc.output_name+".inpcrd"
        self._prmtop = mod_top

        self.log("Building done.")

    def mkdir_p(self,  path):
        if not os.path.isdir(path):
            self.log("mkdir %s" % path)
            os.mkdir(path)

    def check_wd(self):
        import hashlib
        m = hashlib.md5()
        m.update(self.trj_home)
        digest = m.hexdigest()

        if not os.path.isfile("trj_home_md5"):
            with open("trj_home_md5","w") as f:
                f.write(digest)

        old_digest = open("trj_home_md5").read()

        if old_digest != digest:
            if not os.path.samefile(os.curdir, self.trj_home):
                self.log("Not in trj_home folder (%s)" % self.trj_home, MD.FATAL)
            else:
                with open("trj_home_md5", "w") as f:
                    f.write(digest)

    @staticmethod
    def write_file(filename, content):
        if content is not None:
            with open(filename, "w") as f:
                f.write(content)

    def minimize(self):

        self.log("Minimizing...")
        self.check_wd()
        self.mkdir_p(MD._min_dir)

        self.min1_parameters.write_to(MD._min_dir+"/min_1")
        self.min2_parameters.write_to(MD._min_dir+"/min_2")

        self.call_pmemd(MD._min_dir+"/min_1")
        self.call_pmemd(MD._min_dir+"/min_2")

        self.log("Minimizing done.")

    def heat(self):
        self.log("Heating...")
        self.check_wd()
        self.mkdir_p(MD._heat_dir)
        self.heat_parameters.write_to(MD._heat_dir + "/heat")
        self.call_pmemd(MD._heat_dir + "/heat")
        self.log("Heating done.")

    def equilibrate(self):
        self.log("Equilibration...")
        self.check_wd()
        self.mkdir_p(MD._equilibration_dir)
        self.equil_parameters.write_to(MD._equilibration_dir + "/equil")
        self.call_pmemd(MD._equilibration_dir + "/equil")
        self.log("Equilibration done.")

    def do_md_step(self):
        performed_step = self.current_step + 1
        self.log("Running step "+str(performed_step)+"...")
        self.check_wd()
        self.mkdir_p(MD._run_dir)

        step_prefix = self._run_dir + "/run" + MD._pattern % performed_step
        self.run_parameters.write_to(step_prefix)
        self.call_pmemd(step_prefix)

        self._run_trjtool_on(self._run_dir + "/run" + MD._pattern+".nc", performed_step)

        if not self.keep_netcdf:
            os.remove(step_prefix+".nc")

        if not self.keep_restart:
            os.remove(step_prefix+".rst")

        self.current_step = performed_step
        self.log("Step "+str(performed_step)+" done.")
        self.required_steps = [ int(self.current_step) ]
        self.save_state(MD._dump_filename)

    def run_setup(self):
        self.log("Implement your own setup function here", MD.FATAL)

    def run_continue(self):
        self.log("Implement your own continue function here", MD.FATAL)

    def run(self):
        if not self.setup_is_done:
            self.run_setup()
        self.run_continue()

    def call_cmd(self, cmd, abort_on_failure=True):
        """ Returns tuple (exit_code, command_output) """
        print cmd
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
        except Exception as e :
            self.log("Unspecified failure " + e.message + "on command " + " ".join(cmd) + ". Abort.", MD.FATAL)

        # 0 -- success code
        return 0, output

    def call_cmd_pipe(self, cmd, stdin):
        import subprocess
        proc = subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            o, e = proc.communicate(stdin)
        except subprocess.CalledProcessError as e:
            self.log("Process " + " ".join(cmd) + " returned non zero status " + str(e.returncode) + "."
                     "with message" + e.message,
                     MD.ERROR)
            self.log("Output: " + e.output, MD.FATAL)
        except Exception as e :
            self.log("Unspecified failure " + e.message + "on command " + " ".join(cmd) + ". Abort.", MD.FATAL)

        return 0, o

    def _run_trjtool_on(self, netcdf_pattern, step):
        import trjtool

        extract_dict = {
            "reference_structure": self.tleaprc.pdb_output_name+".pdb",
            "netcdf_pattern": netcdf_pattern,
            "netcdf_number": step,
            "frame_stride": "1",
            "frame_first_number": "",
            "frame_last_number": "",
            "segment_ids": "",
            "residue_ids": " ".join(["%d" % r.rId for r in self.restricted_structure]),
            "residue_names": "",
            "atoms": "all",
            "output_filename": os.path.splitext(netcdf_pattern % step)[0] + ".dat",
            "is_ascii": "false",
        }

        trjtool_content = trjtool.get_trjtool_input(extract_dict)

        trjinp_filename = "trjtool.input"
        trjinp = open(trjinp_filename, "w")
        trjinp.write(trjtool_content)
        trjinp.close()

        trjtool_cmd = ["trjtool", trjinp_filename]
        self.call_cmd(trjtool_cmd)


    def call_pmemd(self, prefix):
        cmd = self._pmemd_executable + [
            "-O",
            "-i", prefix + ".in",
            "-o", prefix + ".out",
            "-p", self._prmtop,
            "-c", self._restart_filename,
            "-ref", self._reference_filename if self._reference_filename is not None else self._restart_filename,
            "-x", prefix + ".nc",
            "-r", prefix + ".rst",
            "-inf", prefix + ".mdinfo",
            "-l", prefix + ".log"
        ]
        self.call_cmd(cmd)
        self._restart_filename = prefix + ".rst"

    def get_steps(self):
        import glob
        step_files = sorted(glob.glob(MD._run_dir + "/run" + ("?" * len(self._pattern % 0)) + ".dat"))
        steps = []
        prefix_len = len(MD._run_dir + "/run")
        suffix_len = len(".dat")
        for f in step_files:
            steps.append(int(f[prefix_len:-suffix_len]))
        return sorted(steps)

    def get_frames_in_step(self,step):
        import binfile
        if step < 0:
            step = self.current_step + step+1
        suffix = self._pattern % step
        bf = binfile.Binfile(MD._run_dir + "/" + "run" + suffix + ".dat")
        return len(bf.data)

    def log(self, message, level=INFO):
        """
              :param message: message
              :type message: str
              :param level: level of message
              """
        import socket, time, sys
        if level > MD.DEBUG:
            level = MD.DEBUG
        if level < MD.FATAL:
            level = MD.FATAL
        if level <= self.verbosity:
            hostname = "[" + socket.gethostname() + "]"
            cuda_devices = "[" + os.getenv("CUDA_VISIBLE_DEVICES", "?") + "]"
            md_id = "[" + self._name + "]"
            date_time = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
            level_str = "[" + MD.__msg_level[level] + "]"
            with open(MD._log_filename, "a") as log_file:
                log_string = hostname + cuda_devices + md_id + date_time + level_str + ": " + message + "\n"
                log_file.write(log_string)
                if self.tee_log_to_stdout:
                    sys.stdout.write(log_string)
                    sys.stdout.flush()
        if level == MD.FATAL:
            self._on_fatal()

    def _on_fatal(self):
        import sys
        self.check_wd()
        self.save_state("fatal_state.pickle")
        sys.exit(1)

    @staticmethod
    def load_state(filename, cd_trj_home_on_load=True):
        """
        Returns MD stated, stored in pickle file
        :param filename: MD pickle
        :return: MD loaded from pickle
        :rtype: MD
        """
        import dill

        f = open(filename, "rb")
        if f:
            result = dill.load(f)
            if (cd_trj_home_on_load):
                os.chdir(result.trj_home)
            return result
        else:
            raise OSError("Could not open '%s' for reading." % filename)

    def set_step_as_restart_file(self, step_number=-1):
        """
        :param step_number:
        :type step_number: int
        :return:
        """
        if step_number < 0:
            step_number = self.current_step + step_number + 1

        self._restart_filename = MD._run_dir + "/" + "run" + MD._pattern % step_number + ".rst"

    def save_state(self, filename):
        """
        Serialize MD state into marshal file
        :param filename:
        :type filename: str
        :return:
        """
        import dill
        import shutil
        if filename is None:
            filename = MD._dump_filename
        filename = os.path.abspath(filename)
        out = open(filename+".bak", 'wb')
        if out:
            self.log("Writing dump to %s " % filename)
            dill.dump(self, out)
            out.close()
        else:
            self.log("Could not open file %s to write" % filename, MD.FATAL)
        shutil.move(filename + ".bak", filename)

    def get_type_of(self, mask):
        import StringIO, sys
        output = StringIO.StringIO("")

        from ParmedTools.parmed_cmd import ParmedCmd
        from ParmedTools.parmlist import ParmList
        from ParmedTools.exceptions import (ParmError, InterpreterError)

        amber_prmtop = ParmList()
        amber_prmtop.add_parm(self.tleaprc.output_name+".mod.prmtop")

        command = StringIO.StringIO("printLJTypes " + mask)

        parmed_commands = ParmedCmd(amber_prmtop, stdin=command, stdout=output)
        parmed_commands.use_rawinput = 0
        # parmed_commands.interpreter = opt.interpreter
        parmed_commands.prompt = ''
        # Loop through all of the commands
        try:
            parmed_commands.cmdloop()
        except InterpreterError, err:
            sys.exit('%s: %s' % (type(err).__name__, err))
        except ParmError:
            # This has already been caught and printed. If it was re-raised, then
            # that means we wanted to exit
            sys.exit(1)

        # DANGEROUS PARSING  ^_^
        lines = output.getvalue().split("\n")
        import re
        return int(re.split("\s+",lines[3].strip())[-1])

    def get_chains(self):
        return readPdb(self.tleaprc.pdb_output_name+".pdb")[0]

    def put_frame(self, atoms, step, frame):
        from binfile import Binfile

        if step < 0:
            step = self.current_step + step + 1

        frames_per_step = self.run_parameters["nstlim"] / self.run_parameters["ntwx"]
        if frame < 0:
            frame = frames_per_step + frame

        assert 0 <= frame < frames_per_step, "Frame number is too big"
        assert 0 <= step  <= self.current_step, "Step is too big"

        binfile = Binfile(MD._run_dir+"/run"+MD._pattern % step+".dat")
        assert binfile.get_hash() == atoms.get_hash(), "Atoms (%s) does not match to binfile (%s)"%(binfile.get_hash(), atoms.get_hash())
        binfile.putmat(frame, atoms)
