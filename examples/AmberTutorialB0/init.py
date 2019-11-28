from amber_runner.MD import *


class Prepare(Step):
    def run(self, md: 'AmberTutorialB0'):
        tleap_in: TleapInput = md.build.tleap.input
        tleap_in.source('leaprc.protein.ff14SB')
        tleap_in.source('leaprc.water.tip3p')
        tleap_in.add_command(f'{tleap_in.frame} = sequence {{ ACE ALA NME }}')
        tleap_in.solvate_oct("TIP3PBOX", 10.0)
        tleap_in.save_amber_params()
        tleap_in.quit()

        md.minimize.input.cntrl(
            imin=1,
            ntx=1,
            irest=0,
            maxcyc=20,
            ncyc=10,
            ntpr=10,
            ntwx=0,
            cut=8.0,
        )
        md.heat.input.cntrl(
            imin=0,
            ntx=1,
            irest=0,
            nstlim=10000,
            dt=0.002,
            ntf=2,
            ntc=2,
            tempi=0.0,
            temp0=300.0,
            ntpr=100,
            ntwx=100,
            cut=8.0,
            ntb=1,
            ntp=0,
            ntt=3,
            gamma_ln=2.0,
            nmropt=1,
            ig=-1,
        )

        md.heat.input.varying_conditions.add(
            type='TEMP0', istep1=0, istep2=9000, value1=0.0, value2=300.0
        ).add(
            type='TEMP0', istep1=9001, istep2=10000, value1=300.0, value2=300.0
        )

        md.production.input.cntrl(
            imin=0,
            ntx=5,
            irest=1,
            nstlim=30000,
            dt=0.002,
            ntf=2,
            ntc=2,
            temp0=300.0,
            ntpr=100,
            ntwx=100,
            cut=8.0,
            ntb=2,
            ntp=1,
            ntt=3,
            gamma_ln=2.0,
            ig=-1,
        )


class Analysis(Step):

    def run(self, md: 'AmberTutorialB0'):
        import subprocess
        import os

        summary = md.mkdir_p(self.step_dir / "summary").absolute()

        subprocess.run([
            "process_mdout.perl",
            (md.heat.step_dir / f"{md.heat.name}.out").absolute(),
            (md.production.step_dir / f"{md.production.name}.out").absolute()
        ], cwd=str(summary))

        with remote_runner.utility.ChangeDirectory(self.step_dir):
            temp = self.read_summary(summary / "summary.TEMP")
            density = self.read_summary(summary / "summary.DENSITY")
            etot = self.read_summary(summary / "summary.ETOT")
            eptot = self.read_summary(summary / "summary.EPTOT")
            ektot = self.read_summary(summary / "summary.EKTOT")

            import matplotlib.pyplot as plt

            plt.plot(temp.time, temp.value)
            plt.ylabel("temperature, K")
            plt.xlabel("time, ps")
            plt.savefig("TEMP.png")
            plt.close()

            plt.plot(density.time, density.value)
            plt.ylabel("density, g/cm^3")
            plt.xlabel("time, ps")
            plt.savefig("DENSITY.png")
            plt.close()

            plt.plot(ektot.time, ektot.value, label="EKTOT", color="red")
            plt.plot(eptot.time, eptot.value, label="EPTOT", color="green")
            plt.plot(etot.time, etot.value, label="ETOT", color="black")
            plt.ylabel("energy, Kcal/mol")
            plt.xlabel("time, ps")
            plt.savefig("ENERGY.png")
            plt.close()

    def read_summary(self, summary_path):
        import pandas as pd
        return pd.read_csv(summary_path, sep=r"\s+", names=["time", "value"])


class AmberTutorialB0(MdProtocol):
    def __init__(self):
        wd = Path("B0")
        self.mkdir_p(wd)
        MdProtocol.__init__(self, name="B0", wd=wd)
        self.sander = PmemdCommand()
        self.sander.executable = ["pmemd.cuda"]
        self.sander.allow_small_box = True
        self.prepare = Prepare("prepare")
        self.build = Build("build")
        self.minimize = SingleSanderCall("minimize")
        self.heat = SingleSanderCall("heat")
        self.production = SingleSanderCall("prod")
        self.analysis = Analysis("analysis")


md = AmberTutorialB0()
md.save(Path("B0/state.dill"))
