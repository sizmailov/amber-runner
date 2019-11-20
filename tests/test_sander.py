from amber_runner.executables import PmemdCommand


def test_pmemd_command():
    pmemd = PmemdCommand()

    assert pmemd.args == ['-i', 'run.in', '-o', 'run.out', '-r', 'run.rst', '-O']
    pmemd.output_prefix = f"run{212:05d}"
    assert pmemd.args == ['-i', 'run00212.in', '-o', 'run00212.out', '-r', 'run00212.rst', '-O']

    with pmemd.scope_args(output_prefix=f"run{512:05d}"):
        assert pmemd.args == ['-i', 'run00512.in', '-o', 'run00512.out', '-r', 'run00512.rst', '-O']

    assert pmemd.args == ['-i', 'run00212.in', '-o', 'run00212.out', '-r', 'run00212.rst', '-O']

    assert pmemd.executable == ["pmemd"]
