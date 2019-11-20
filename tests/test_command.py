from amber_runner.command import ArgumentFactory, Command
import pytest


class MyCommand(Command):
    def __init__(self):
        super().__init__()
        arg_factory = ArgumentFactory(self)

        self.message = arg_factory.string("--message", "hello")
        self.flag = arg_factory.boolean("--flag", True)
        self.default = arg_factory.boolean("--default")
        self.extra = arg_factory.string("--extra")
        self.message_length = arg_factory.lambda_string("--message-length", lambda: f"{len(self.message)}")
        self.captured_message = arg_factory.lambda_string("--message-duplicate", lambda: f"{self.message}")
        self.include_directory = arg_factory.list("--include-directory")
        self.names = arg_factory.list("--name", ["A", "B"])

        self.enable_cuda = False


def test_construction():
    cmd = MyCommand()

    assert cmd.message == "hello"
    assert cmd.captured_message == "hello"
    assert cmd.flag is True
    assert cmd.extra is None
    assert cmd.default is None
    assert cmd.message_length == "5"

    assert cmd.enable_cuda is False

    assert cmd.args == ["--message", "hello",
                        "--flag",
                        "--message-length", "5",
                        "--message-duplicate", "hello",
                        "--name", "A",
                        "--name", "B",
                        ]


def test_setter():
    cmd = MyCommand()

    cmd.message = ", world!"
    cmd.default = True
    cmd.extra = "/opt/"
    cmd.flag = False
    cmd.enable_cuda = True
    cmd.include_directory = ["~/.local/include", "/usr/local/include"]

    assert cmd.captured_message == ", world!"
    assert cmd.message == ", world!"
    assert cmd.message_length == "8"
    assert cmd.extra is "/opt/"
    assert cmd.default is True
    assert cmd.flag is False

    assert cmd.enable_cuda is True

    assert cmd.args == ["--message", ", world!",
                        "--default",
                        "--extra", "/opt/",
                        "--message-length", "8",
                        "--message-duplicate", ", world!",
                        "--include-directory", "~/.local/include",
                        "--include-directory", "/usr/local/include",
                        "--name", "A",
                        "--name", "B",
                        ]

    with pytest.raises(AttributeError):
        cmd.message_length = 12


def test_temp_args():
    cmd = MyCommand()

    with cmd.scope_args(message="tmp") as exe:
        assert exe is cmd
        assert exe.message == "tmp"

    assert cmd.message == "hello"
