from typing import Dict, Any, List, Callable
import subprocess


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
        self.name = name
        self.lambda_ = lambda_

    @property
    def value(self):
        return self.lambda_()


class StringArgument(StringArgumentMixin):

    def __init__(self, name, value: str):
        self.name = name
        self.value = value


class BooleanArgument(BooleanArgumentMixin):

    def __init__(self, name, value: bool):
        self.name = name
        self.value = value


class ListArgument(ListArgumentMixin):

    def __init__(self, name, value: List):
        self.name = name
        self.value = value


class OptionalStringArgument(OptionalArgumentMixin, StringArgument):
    pass


class OptionalBooleanArgument(OptionalArgumentMixin, BooleanArgument):
    pass


class OptionalListArgument(OptionalArgumentMixin, ListArgument):
    pass


class ArgumentFactory:

    def __init__(self, instance):
        self.instance = instance

    def lambda_string(self, name, lambda_: Callable[[], str]):
        arg = LambdaStringArgument(name, lambda_)
        self.instance.arguments.append(arg)
        return arg

    def string(self, name, value: str = None):
        if value is None:
            arg = OptionalStringArgument(name, value)
        else:
            arg = StringArgument(name, value)
        self.instance.arguments.append(arg)
        return arg

    def boolean(self, name, value: bool = None):
        if value is None:
            arg = OptionalBooleanArgument(name, value)
        else:
            arg = BooleanArgument(name, value)
        self.instance.arguments.append(arg)
        return arg

    def list(self, name, value: List = None):
        if value is None:
            arg = OptionalListArgument(name, value)
        else:
            arg = ListArgument(name, value)
        self.instance.arguments.append(arg)
        return arg


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
    arguments: List[Argument]

    def __init__(self):
        self.arguments = []

    def __setattr__(self, key, value):
        if not hasattr(self, key):
            super().__setattr__(key, value)
        else:
            attr = super().__getattribute__(key)
            if isinstance(attr, Argument):
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
        for arg in self.arguments:
            result.extend(arg.args())
        return result

    @property
    def cmd(self):
        return self.executable + self.args

    def run(self, **kwargs):
        return subprocess.run(self.cmd, **kwargs)

    def check_call(self, **kwargs):
        return subprocess.check_call(self.cmd, **kwargs)

    def check_output(self, **kwargs):
        return subprocess.check_output(self.cmd, **kwargs)
