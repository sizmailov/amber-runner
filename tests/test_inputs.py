import io
from pathlib import Path

import pytest
from remote_runner.utility import ChangeToTemporaryDirectory

from amber_runner.inputs import AmberInput, FlatWelledParabola


def test_amber_input_empty():
    inp = AmberInput()

    with ChangeToTemporaryDirectory():
        test_in = Path("test.in")
        with open(test_in, "w") as f:
            inp.write(f)

        assert test_in.exists()
        assert not Path(f"{test_in}.restraints").exists()


def test_set_by_kwargs():
    inp = AmberInput()

    inp.cntrl(
        imin=1,
        maxcyc=500,
        ncyc=100,
        ntb=2,
        ntr=1,
        cut=10.0
    )

    assert inp.cntrl["imin"] == 1
    assert inp.cntrl["maxcyc"] == 500
    assert inp.cntrl["ncyc"] == 100
    assert inp.cntrl["ntb"] == 2
    assert inp.cntrl["ntr"] == 1
    assert inp.cntrl["cut"] == 10.0


def test_restraints():
    inp = AmberInput()
    inp.cntrl(nmropt=1
              )
    inp.restraints.distance(1, 2, FlatWelledParabola(1, 2, 3, 4, 5, 6))
    inp.restraints.distance(3, 4, FlatWelledParabola(1, 2, 3, 4, 5, 6))
    inp.restraints.angle(1, 2, 3, FlatWelledParabola(1, 2, 3, 4, 5, 6))
    inp.restraints.dihedral(1, 2, 3, 4, FlatWelledParabola(1, 2, 3, 4, 5, 6))

    with ChangeToTemporaryDirectory():
        test_in = Path("test.in")
        with open(test_in, "w") as f:
            inp.write(f)

        assert test_in.exists()
        test_in_restraints = Path(f"{test_in}.disang")
        assert test_in_restraints.exists()

        assert test_in.open().read().strip() == """Generated by amber_runner
&cntrl
    nmropt = 1
/
DISANG=test.in.disang
""".strip()
        assert test_in_restraints.open().read().strip() == """
&rst  !
     iat=1,2, r1=1, r2=2, r3=3, r4=4,
     rk2=5, rk3=6
&end

&rst  !
     iat=3,4, r1=1, r2=2, r3=3, r4=4,
     rk2=5, rk3=6
&end

&rst  !
     iat=1,2,3, r1=1, r2=2, r3=3, r4=4,
     rk2=5, rk3=6
&end

&rst  !
     iat=1,2,3,4, r1=1, r2=2, r3=3, r4=4,
     rk2=5, rk3=6
&end
""".strip()


def test_groups():
    inp = AmberInput()

    inp.pin(
        AmberInput.GroupSelection(
            title="My Group 1",
            weight=100.0,
            find=[AmberInput.GroupSelectionFind(atom_name="CA"),
                  AmberInput.GroupSelectionFind(atom_type="X"),
                  AmberInput.GroupSelectionFind(tree_type="M"),
                  AmberInput.GroupSelectionFind(residue_name="CYS")
                  ],
            atom_id_ranges=[(1, 100)],
            residue_id_ranges=[(5, 10)]
        )).pin(
        AmberInput.GroupSelection(
            title="My Group 2",
            weight=100.0,
            atom_id_ranges=[(1, 100)]
        ),
    )

    with ChangeToTemporaryDirectory():
        test_in = Path("test.in")
        with open(test_in, "w") as f:
            inp.write(f)
        assert test_in.open().read().strip() == """Generated by amber_runner
My Group 1
100.0
FIND
CA * * *
* X * *
* * M *
* * * CYS
SEARCH
ATOM 1 100
RES 5 10
END
My Group 2
100.0
ATOM 1 100
END
END
""".strip()


def test_redirections():
    inp = AmberInput()

    with pytest.raises(AssertionError):
        inp.redirect("XXXX", "tmp.distances")

    inp.redirect("DISANG", "tmp.distances")

    with io.StringIO() as f:
        inp.write(f)

        assert f.getvalue().strip() == """Generated by amber_runner
DISANG=tmp.distances
""".strip()


def test_varying_conditions():
    inp = AmberInput()
    inp.varying_conditions.add(
        type='TEMP0', istep1=1000, istep2=2000,
        value1=300.0, value2=10.0, iinc=5
    ).add(
        type='VDW', istep1=0, istep2=1500,
        value1=1.0, value2=2.0, iinc=0
    )

    with io.StringIO() as f:
        inp.write(f)
        assert f.getvalue().strip() == """Generated by amber_runner
&wt
    type = 'TEMP0'
    istep1 = 1000
    istep2 = 2000
    value1 = 300.0
    value2 = 10.0
    iinc = 5
/

&wt
    type = 'VDW'
    istep1 = 0
    istep2 = 1500
    value1 = 1.0
    value2 = 2.0
    iinc = 0
/

&wt
    type = 'END'
/


        
        """.strip()


def test_all_together():
    inp = AmberInput()

    inp.cntrl(
        imin=1,
        maxcyc=500,
        ncyc=100,
        ntb=2,
        ntr=1,
        cut=10.0
    )

    inp.varying_conditions.add(
        type='TEMP0', istep1=1000, istep2=2000,
        value1=300.0, value2=10.0, iinc=5
    ).add(
        type='VDW', istep1=0, istep2=1500,
        value1=1.0, value2=2.0, iinc=0
    )

    inp.group_selections.extend([
        AmberInput.GroupSelection(
            title="My Group 1",
            weight=100.0,
            find=[AmberInput.GroupSelectionFind(atom_name="CA"),
                  AmberInput.GroupSelectionFind(atom_type="X"),
                  AmberInput.GroupSelectionFind(tree_type="M"),
                  AmberInput.GroupSelectionFind(residue_name="CYS")
                  ],
            atom_id_ranges=[(1, 100)],
            residue_id_ranges=[(5, 10)]
        ),
        AmberInput.GroupSelection(
            title="My Group 2",
            weight=100.0,
            atom_id_ranges=[(1, 100)]
        ),
    ])

    inp.redirect("DISANG", "tmp.distances")

    with ChangeToTemporaryDirectory():
        test_in = Path("test.in")
        with open(test_in, "w") as f:
            inp.write(f)

        # print(test_in.open().read())
        assert test_in.open().read().strip() == """Generated by amber_runner
&cntrl
    imin = 1
    maxcyc = 500
    ncyc = 100
    ntb = 2
    ntr = 1
    cut = 10.0
/
&wt
    type = 'TEMP0'
    istep1 = 1000
    istep2 = 2000
    value1 = 300.0
    value2 = 10.0
    iinc = 5
/

&wt
    type = 'VDW'
    istep1 = 0
    istep2 = 1500
    value1 = 1.0
    value2 = 2.0
    iinc = 0
/

&wt
    type = 'END'
/
DISANG=tmp.distances
My Group 1
100.0
FIND
CA * * *
* X * *
* * M *
* * * CYS
SEARCH
ATOM 1 100
RES 5 10
END
My Group 2
100.0
ATOM 1 100
END
END

""".strip()
