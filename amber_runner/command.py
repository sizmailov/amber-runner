import subprocess
import typing
from collections import OrderedDict
from typing import Any, List
from remote_runner.utility import self_logger as _logger


class Argument:
    name: str
    value: Any

    def args(self) -> List[str]:
        raise NotImplementedError()


class OptionalArgumentMixin(Argument):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def args(self) -> List[str]:
        if self.value is not None:
            return super().args()
        else:
            return []


class StringArgumentMixin(Argument):

    def args(self) -> List[str]:
        return [self.name, self.value]


class ListArgumentMixin(Argument):

    def args(self) -> List[str]:
        result = []
        for val in self.value:
            result.extend([self.name, str(val)])
        return result


class BooleanArgumentMixin(Argument):

    def args(self):
        if self.value:
            return [self.name]
        else:
            return []


class LambdaStringArgument(StringArgumentMixin):

    def __init__(self, name, lambda_):
        if not hasattr(lambda_, '__call__'):
            raise RuntimeError(f"`lambda_` argument of LambdaStringArgument() must be callable")
        self.name = name
        self.lambda_ = lambda_

    @property
    def value(self):
        return self.lambda_()


class StringArgument(StringArgumentMixin):

    def __init__(self, name, value: str = None):
        self.name = name
        self.value = value


class BooleanArgument(BooleanArgumentMixin):

    def __init__(self, name, value: bool = None):
        self.name = name
        self.value = value


class ListArgument(ListArgumentMixin):

    def __init__(self, name, value: List = None):
        self.name = name
        self.value = value


class OptionalStringArgument(OptionalArgumentMixin, StringArgument):
    pass


class OptionalBooleanArgument(OptionalArgumentMixin, BooleanArgument):
    pass


class OptionalListArgument(OptionalArgumentMixin, ListArgument):
    pass


class ScopeArguments:
    """
    Allows to temporary alter command arguments
    Restores original values on exit
    """

    def __init__(self, command, tmp_kwargs):
        self.command = command
        self.tmp_args = tmp_kwargs
        self.backup = {}

    def __enter__(self):
        for k, v in self.tmp_args.items():
            attr = getattr(self.command, k, v)
            setattr(self.command, k, v)
            self.backup[k] = attr

        return self.command

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, v in self.backup.items():
            setattr(self.command, k, v)


class Command:
    executable: List[str]
    arguments: OrderedDict  # type:typing.OrderedDict [str, Argument]

    def __init__(self):
        self.arguments = OrderedDict()

    def __setattr__(self, key, value):
        if isinstance(value, Argument):
            self.arguments[value.name] = value
        if not hasattr(self, key):
            super().__setattr__(key, value)
        else:
            attr = super().__getattribute__(key)
            if isinstance(attr, Argument) and not isinstance(value, Argument):
                attr.value = value
            else:
                super().__setattr__(key, value)

    def __getattribute__(self, item):
        attr = super().__getattribute__(item)
        if isinstance(attr, Argument):
            return attr.value
        else:
            return attr

    def scope_args(self, **kwargs):
        return ScopeArguments(self, kwargs)

    @property
    def args(self):
        result = []
        for arg in self.arguments.values():
            result.extend(arg.args())
        return result

    @property
    def cmd(self):
        return self.executable + self.args

    def run(self, check=True, **kwargs):
        _logger(self).info(self.cmd)
        return subprocess.run(self.cmd, check=check, **kwargs)

    def check_call(self, **kwargs):
        _logger(self).info(self.cmd)
        return subprocess.check_call(self.cmd, **kwargs)

    def check_output(self, **kwargs):
        _logger(self).info(self.cmd)
        return subprocess.check_output(self.cmd, **kwargs)
