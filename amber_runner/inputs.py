from typing import List, Tuple, Union, TextIO, OrderedDict, Dict, Any, Callable, Generic, TypeVar  # , Literal
import os
import f90nml

T = TypeVar
ResidueId = int
AtomId = int
RestraintAtomIdTuple = Union[Tuple[AtomId, AtomId],
                             Tuple[AtomId, AtomId, AtomId],
                             Tuple[AtomId, AtomId, AtomId, AtomId]]

GroupTreeType = str  # Literal["M", "S", "B", "3", "E", "*"]


class InputWriter:

    def write(self, output: TextIO):
        raise NotImplementedError()


class Namelist(f90nml.namelist.Namelist):

    def __call__(self, *args, **kwargs):
        assert len(args) == 0, "args are disallowed"
        for k, v in kwargs.items():
            self[k] = v


class TleapInput(InputWriter):
    frame = "frame"

    def __init__(self, outdir="1_build"):
        self.commands: List[str] = []
        self.outdir = outdir

    @property
    def frame_basename(self):
        return os.path.join(self.outdir, self.frame)

    def add_command(self, command: str):
        self.commands.append(command)

    def write(self, output: TextIO):
        output.write("\n".join(self.commands))
        if self.commands[-1:] != ["quit"]:
            output.write("\nquit")

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

    def quit(self):
        self.add_command("quit")


class ParmedInput(InputWriter):
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

    def write(self, output: TextIO):
        output.write("\n".join(self.commands))


class FlatWelledParabola:

    def __init__(self, r1: float, r2: float, r3: float, r4: float, k2: float, k3: float):
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3
        self.r4 = r4
        self.k2 = k2
        self.k3 = k3


class AmberNMRRestraints(Dict[RestraintAtomIdTuple, List[FlatWelledParabola]], InputWriter):

    def add(self, atoms: RestraintAtomIdTuple, penalty: FlatWelledParabola):
        if atoms not in self:
            self[atoms] = []
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

    def write(self, output: TextIO):
        for ats, penalties in self.items():
            cs_ats = ','.join(map(str, ats))
            for penalty in penalties:
                output.write(f"""
&rst  ! 
     iat={cs_ats}, r1={penalty.r1}, r2={penalty.r2}, r3={penalty.r3}, r4={penalty.r4},
     rk2={penalty.k2}, rk3={penalty.k3}
&end
""")


class AmberInput(InputWriter):
    class VaryingConditions:
        def __init__(self):
            self.wts: List[Dict] = []

        def add(self, **kwargs):
            assert "type" in kwargs
            assert kwargs["type"] != "END", 'Redundant wt namelist type=END. It\' is added automatically'
            self.wts.append(Namelist(**kwargs))
            return self

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
                     title: str,
                     weight: float = None,
                     find: List['AmberInput.GroupSelectionFind'] = None,
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
            for first, last in self.residue_id_ranges:
                out.write(f"RES {first} {last}\n")
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

        TypesLiteral = str

        def __setitem__(self, key, value):
            assert key in self.allowed_types
            super().__setitem__(key, value)

        def write(self, out: TextIO):
            for key, value in self.items():
                out.write(f"{key}={value}\n")

    def __init__(self):
        self.namelist = Namelist()
        self.varying_conditions = AmberInput.VaryingConditions()
        self.restraints = AmberNMRRestraints()
        self.group_selections = AmberInput.GroupSelections()
        self.file_redirections = AmberInput.FileRedirections()

    def pin(self, group_selection: GroupSelection):
        self.group_selections.append(group_selection)
        return self

    def redirect(self, file_type: FileRedirections.TypesLiteral, filename: str):
        self.file_redirections[file_type] = filename
        return self

    def write(self, output: TextIO):
        title = "Generated by amber_runner"

        if len(self.restraints) > 0:
            assert "nmropt" in self.cntrl and self.cntrl["nmropt"] > 0
            with open(f"{output.name}.restraints", "w") as rout:
                self.restraints.write(rout)

        output.write(f"{title}\n")
        self.namelist.write(output)
        self.varying_conditions.write(output)
        self.file_redirections.write(output)
        self.group_selections.write(output)

    @property
    def cntrl(self) -> Namelist:
        return self._get("cntrl")

    @property
    def ewald(self) -> Namelist:
        return self._get("ewald")

    @property
    def qmmm(self) -> Namelist:
        return self._get("qmmm")

    @property
    def pb(self) -> Namelist:
        return self._get("pb")

    @property
    def amoeba(self) -> Namelist:
        return self._get("amoeba")

    @property
    def debugf(self) -> Namelist:
        return self._get("debugf")

    @property
    def emap(self) -> Namelist:
        return self._get("emap")

    def _get(self, name):
        if name not in self.namelist:
            self.namelist[name] = Namelist()
        return self.namelist[name]
