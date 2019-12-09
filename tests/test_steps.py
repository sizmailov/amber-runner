import pytest
from amber_runner.MD import RepeatedSanderCall


def test_RepeatedSanderCall_is_complete():
    x = RepeatedSanderCall("run", 10)
    assert not x.is_complete
    x.is_complete = False

    x.current_step = 9
    with pytest.raises(AssertionError):
        x.is_complete = True

    x.current_step = 10
    assert x.is_complete
    x.is_complete = True
    with pytest.raises(AssertionError):
        x.is_complete = False
