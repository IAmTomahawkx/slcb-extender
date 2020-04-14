#!python2
# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-2019 Rapptz, IAmTomahawkx

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import sys
import inspect
import calendar
import traceback
from collections import OrderedDict

from .errors import *
from .cooldowns import *
from . import errors
from . import converters
from .abc import RestOfInput, BotBase, Union, Optional, User

__all__ = [
    "GroupMapping",
    "command",
    "Command",
    "user_cooldown",
    "global_cooldown",
    "group",
    "Group"
]


def p():
    pass

_function_type = type(p)
del p


class _Base:
    pass


class _CaseInsensitiveDict(dict):
    def __contains__(self, k):
        return dict.__contains__(self, k.lower())

    def __delitem__(self, k):
        return dict.__delitem__(self, k.lower())

    def __getitem__(self, k):
        return dict.__getitem__(self, k.lower())

    def get(self, k, default=None):
        return dict.get(self, k.lower(), default)

    def pop(self, k, default=None):
        return dict.pop(self, k.lower(), default)

    def __setitem__(self, k, v):
        dict.__setitem__(self, k.lower(), v)


class GroupMapping:
    """A mixin that implements common functionality for classes that behave
    similar to :class:`.Group` and are allowed to register commands.

    the GroupMapping is code mostly taken from rapptz' discord.py library. credit goes to him.

    Attributes
    -----------
    all_commands: :class:`dict`
        A mapping of command name to :class:`.Command` or subclass
        objects.
    case_insensitive: :class:`bool`
        Whether the commands should be case insensitive. Defaults to ``False``.
    """

    def __init__(self, *args, **kwargs):
        case_insensitive = kwargs.get('case_insensitive', False)
        self.all_commands = _CaseInsensitiveDict() if case_insensitive else {}
        self.case_insensitive = case_insensitive

    @property
    def commands(self):
        """Set[:class:`.Command`]: A unique set of commands without aliases that are registered."""
        return set(self.all_commands.values())

    def recursively_remove_all_commands(self):
        for command in self.all_commands.copy().values():
            if isinstance(command, GroupMapping):
                command.recursively_remove_all_commands()
            self.remove_command(command.name)

    def add_command(self, command):
        """Adds a :class:`.Command` or its subclasses into the internal list
        of commands.

        This is usually not called, instead the :meth:`~.GroupMapping.command` or
        :meth:`~.GroupMixin.group` shortcut decorators are used instead.

        Parameters
        -----------
        command: :class:`Command`
            The command to add.

        Raises
        -------
        :exc:`.BotException`
            If the command is already registered.
        TypeError
            If the command passed is not a subclass of :class:`.Command`.
        """

        if not isinstance(command, Command):
            raise TypeError('The command passed must be a subclass of Command')

        if isinstance(self, Command):
            command.parent = self

        if isinstance(self, BotBase):
            if isinstance(command, Group):
                command._set_bot(self)
            else:
                command._attach(self)

        elif self._bot is not None:
            if isinstance(command, Group):
                command._set_bot(self._bot)
            else:
                command._attach(self._bot)

        if command.name in self.all_commands:
            raise BotException(
                'Command {0.name} is already registered.'.format(command))

        self.all_commands[command.name] = command
        for alias in command.aliases:
            if alias in self.all_commands:
                raise BotException(
                    'The alias {} is already an existing command or alias.'.
                        format(alias))
            self.all_commands[alias] = command
        return command

    def remove_command(self, name):
        """Remove a :class:`.Command` or subclasses from the internal list
        of commands.

        This could also be used as a way to remove aliases.

        Parameters
        -----------
        name: :class:`str`
            The name of the command to remove.

        Returns
        --------
        :class:`.Command` or subclass
            The command that was removed. If the name is not valid then
            `None` is returned instead.
        """
        command = self.all_commands.pop(name, None)

        # does not exist
        if command is None:
            return None

        if name in command.aliases:
            # we're removing an alias so we don't want to remove the rest
            return command

        # we're not removing the alias so let's delete the rest of them.
        for alias in command.aliases:
            self.all_commands.pop(alias, None)
        return command

    def walk_commands(self):
        """An iterator that recursively walks through all commands and subcommands."""
        for command in tuple(self.all_commands.values()):
            yield command
            if isinstance(command, GroupMapping):
                for comm in command.walk_commands():
                    yield comm

    def get_command(self, name):
        """Get a :class:`.Command` or subclasses from the internal list
        of commands.

        This could also be used as a way to get aliases.

        The name could be fully qualified (e.g. ``'foo bar'``) will get
        the subcommand ``bar`` of the group command ``foo``. If a
        subcommand is not found then ``None`` is returned just as usual.

        Parameters
        -----------
        name: :class:`str`
            The name of the command to get.

        Returns
        --------
        :class:`Command` or subclass
            The command that was requested. If not found, returns ``None``.
        """

        # fast path, no space in name.
        if ' ' not in name:
            return self.all_commands.get(name)

        names = name.split()
        obj = self.all_commands.get(names[0])
        if not isinstance(obj, GroupMapping):
            return obj

        for name in names[1:]:
            try:
                obj = obj.all_commands[name]
            except (AttributeError, KeyError):
                return None

        return obj

    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.GroupMapping.add_command`.
        """

        def decorator(func):
            kwargs.setdefault('parent', self)
            if isinstance(self, Node):
                result = command(*args, node=self, **kwargs)(func)
            else:
                result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.group` and adds it to
        the internal command list via :meth:`~.GroupMapping.add_command`.
        """

        def decorator(func):
            kwargs.setdefault('parent', self)
            if isinstance(self, Node):
                result = group(*args, node=self, **kwargs)(func)
            else:
                result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class Command(_Base):
    """
    the class for all commands registered to the bot. this should never be invoked directly
    this may be subclassed, if so, you must pass your subclass to the *cls* parameter of the :ref:`command` decorator.
    to create a command, use the :meth:`command` decorator, or the :meth:`Group.command` decorator, or the :meth:`Bot.command` decorator.

    Parameters
    ------------
    name: a string to invoke the command. defaults to the function name

    help: the help string

    stream_only: a :class:`bool`, indicating if the command should only be available for the stream chat. defaults to False.

    discord_only: a :class:`bool`, indicating if the command should only be available for the discord chat. defaults to False.

    whisper_only: a :class:`bool`, indicating if the command should only be available via whisper/DM. defaults to False.

    ignore_extra: a :class:`bool` indicating whether extra data passed to the command should be ignored. defaults to True.
    if this is False, :exec:`.TooManyArguments` will be raised

    aliases: a list of strings, the strings are each alternate names the command can be invoked under.

    enabled: a boolean, indicating whether the command is enabled. defaults to True.
    """

    def __init__(self, func, **kwargs):
        self.node = kwargs.get("node", None)
        self._delayed_callback = func
        self._bot = kwargs.get("bot")
        self.help = kwargs.get("help")
        self.stream_only = kwargs.get("stream_only", False)
        self.discord_only = kwargs.get("discord_only", False)
        self.whisper_only = kwargs.get("whisper_only", False)
        self.ignore_extra = kwargs.get("ignore_extra", True)
        if not self.help:
            try:
                self.help = func.__doc__.strip().split("\n")[0]
                # due to twitch\'s "oneliner" thing (stupid irc),
                # the help response can only be one line. this leaves the rest of the docstring for
                # documentation.
            except:
                self.help = "No Help Given"

        self.name = kwargs.get("name") or func.__name__
        self._original_name = self.name
        self.others = kwargs.get("aliases", [])
        if not isinstance(self.others, (list, tuple)):
            raise ValueError("aliases must be a list of strings, not {}".
                             format(self.others.__class__.__name__))

        self.aliases = self.others
        try:
            coolers = func.__coolers__
            mapped_coolers = []
            for cooler in coolers:
                mapped_coolers.append(CooldownMapping(cooler))

        except AttributeError:
            mapped_coolers = list()
        finally:
            self._coolers = mapped_coolers

        self.enabled = kwargs.get("enabled", True)
        try:
            checks = func.__checks__
        except AttributeError:
            checks = []
        finally:
            self._checks = checks

        self.pre_hook = None
        self.post_hook = None
        self._handler = kwargs.get("handler", None)
        parent = kwargs.get("parent")
        self.parent = parent if isinstance(parent, Group) else None

    @property
    def callback(self):
        return self._callback

    def _set_callback(self, function):
        self.module = function.__module__
        self.params = params = OrderedDict()

        # unfortunately, the inspect module does not have the `Signature` API in python 2. there are also
        # no typehints as specified by PEP 484 and PEP 525 in python 2. this leaves us with defaults!
        args = inspect.getargspec(function)
        index = 0

        for no, arg in enumerate(args.args):
            if no == 0 and self.node:
                # this is the node "self" reference. it wont have a default attached to it
                continue

            if no == 0 and not self.node or no == 1 and self.node:
                # this must be the "message" parameter. it shouldn't have a default.
                continue

            # we will assume that all parameters have defaults attached to them.
            if not args.defaults:
                params[arg] = str
            else:
                params[arg] = args.defaults[index]

            index += 1

        self._callback = function

    @property
    def qualified_name(self):
        if self.parent is not None:
            pre = self.parent.qualified_name
        else:
            pre = ""
        return (pre + " " + self.name).strip()

    def can_run(self, msg):
        failed = []
        for check in self._checks:
            # if the check doesnt raise any errors, but fails, append it to a list so we can raise our own error
            if not check(msg):
                failed.append(check)
        if len(failed) > 0:
            raise ChecksFailed("the checks for {0.qualified_name} failed".format(self))

    def _get_converter(self, param):
        converter = param
        if converter is None:
            return converters.StrConverter()

        if inspect.isclass(converter):
            try:
                questionable_converter = converter()
                if isinstance(questionable_converter, converters.Converter):
                    return questionable_converter

            except:
                pass

        if isinstance(converter, converters.Converter):
            return converter

        if not isinstance(converter, converters.Converter):
            if converter is User:
                return converters.UserConverter()

            elif isinstance(converter, bool) or converter is bool:
                return converters.BoolConverter()

            elif isinstance(converter, int) or converter is int:
                return converters.IntConverter()

            elif isinstance(converter, float) or converter is float:
                return converters.FloatConverter()

            elif isinstance(converter, str) or converter is str:
                return converters.StrConverter()

            elif isinstance(converter, type(Optional)):
                try:
                    return self._get_converter(converter.type)
                except ConverterError:
                    return converter.type

            raise ConverterError(
                repr(param) + " is not a subclass of chatbot.Converter")

    def do_transformation(self, msg, wantedtype, slot):
        param = msg.view.get_quoted_word()
        converter = self._get_converter(wantedtype)

        v = self._actual_conversion(msg, converter, param, wantedtype, slot)
        return v

    def _actual_conversion(self, msg, converter, argument, wantedtype, slot):
        try:
            return converter.convert(msg, argument, slot)

        except CommandError as e:
            raise ConversionError(None, converter, e)

        except Exception as exc:
            raise ConversionError('Converting to "{}" failed for parameter "{}".'.format(
                    converter.__name__, wantedtype), converter, exc)

    def do_parameters(self, msg, transform):
        msg.args = args = [msg] if not self.node else [self.node, msg]
        msg.kwargs = kwargs = {}

        msg.view.skip_string(msg.prefix + self.qualified_name)
        index = 0
        for name, wanted_type in self.params.items():
            msg.view.skip_ws()

            if msg.view.eof:
                if type(wanted_type) is type(Optional):
                    kwargs[name] = None
                else:
                    raise MissingArguments("Missing Arguments for call to " + self.qualified_name, name)

            if type(wanted_type) is type(RestOfInput):
                # this must be the last parameter.
                kwargs[name] = msg.view.read_rest()
                break

            if type(wanted_type) is type(Optional):
                if isinstance(wanted_type.type, type(RestOfInput)):
                    kwargs[name] = msg.view.read_rest()
                    break

                try:
                    transformed = self.do_transformation(msg, wanted_type.type, index)
                    kwargs[name] = transformed
                except:
                    msg.view.undo()
                    kwargs[name] = None

            if type(wanted_type) is type(Union):
                transformed = None
                for attempt in wanted_type.types:
                    try:
                        transformed = self.do_transformation(msg, attempt, index)
                        kwargs[name] = transformed
                        break

                    except:
                        msg.view.undo()
                        continue

                if transformed is None:
                    raise BadUnionArgument(wanted_type, "Failed to convert '{0}' to any of {1}".format(
                        msg.view.get_quoted_word(), ", ".join(str(x) for x in wanted_type.types)))

            if transform:
                transformed = self.do_transformation(msg, wanted_type, index)
                kwargs[name] = transformed
            else:
                kwargs[name] = msg.view.get_quoted_word()

            index += 1

        if not self.ignore_extra:
            if not msg.view.eof:
                raise TooManyArguments('Too many arguments passed to ' +
                                       self.qualified_name)

    def _attach(self, bot):
        self._bot = bot
        self._set_callback(self._delayed_callback)
        self.namer(bot)

    def namer(self, bot):
        if self._original_name.startswith("settings::"):
            name = self._original_name.replace("settings::", "", 1)
            if hasattr(bot.settings, name):
                self.name = getattr(bot.settings, name)
                if bot.prefix in self.name:
                    self.name = self.name.replace(bot.prefix, "", 1)
            else:
                raise ValueError("Invalid setting: {0} when trying to fetch command name from settings file. "
                                 "The setting: {0} does not exist. command: {1}".format(name, self._original_name))

    def dispatch(self, message):
        """
        this should not be invoked directly. it is exposed for documentation purposes only (AKA my own sanity).

        where the command is run from by the :class:`Bot`
        if you wish to change how dispatch operates, you should be overriding Bot._do_dispatch in your subclass.

        if an error is raised, one of several things could happen.
        a) if a handler is declared for the command (or the node, if the command belongs to one),
        all errors will be sent there. ignore all other possibilities
        b) if the error is a subclass of :exec:`CommandError`, the error will be sent to :meth:`Bot.command_error`
        c) otherwise, the error will be sent to :meth:`Bot.error`

        """
        try:
            self._do_dispatch(message)
        except errors.CommandError as e:
            message.bot.dispatch("command_error", message, e, sys.exc_info()[2])

        except Exception as e:
            v = ExceptionCaught("Command {0}".format(self.qualified_name), e)
            message.bot.dispatch("command_error", message, v, sys.exc_info()[2])

    def _do_dispatch(self, msg, run_checks=True):
        if run_checks:
            # run the checks first
            self.can_run(msg)
            # checks succeeded, now check the cooldown(s)
            self._do_cooldowns(msg)
            # cooldown(s) are ok, now get the parameters

        self.do_parameters(msg, True)

        if self.pre_hook is not None:
            try:
                self.pre_hook(msg)
            except:
                # ignore any exceptions that come from the pre/post hooks
                pass

        # run the command function
        self.callback(*msg.args, **msg.kwargs)

        if self.post_hook is not None:
            try:
                self.post_hook(msg)
            except:
                pass

    def _do_cooldowns(self, msg):
        for cooler in self._coolers:
            if cooler.valid:
                current = msg.timestamp.replace(
                    tzinfo=None)
                current = calendar.timegm(current.timetuple())
                bucket = cooler.get_bucket(msg, current)
                retry_after = bucket.update_rate_limit(current)
                if retry_after:
                    raise bucket.error(bucket, retry_after)

    def __repr__(self):
        return "<Command {0} at {1} node: {2}>".format(self.qualified_name, hex(id(self)), self.node)


class Group(GroupMapping, Command):
    def __init__(self, func, **kwargs):
        self.dispatch_without_command = kwargs.get("dispatch_without_command", True)
        GroupMapping.__init__(self, **kwargs)
        Command.__init__(self, func, **kwargs)

    def _set_bot(self, bot):
        for command in self.commands:
            if isinstance(command, Group):
                command._set_bot(bot)
            else:
                command._attach(bot)
        self._bot = bot

    def _find_command(self, view):
        maybe_subcommand = view.get_word()
        if maybe_subcommand in self.commands:
            if isinstance(self.all_commands[maybe_subcommand], Group):
                view.skip_ws()
                return self.all_commands[maybe_subcommand]._find_command(view)

            else:
                return self.all_commands[maybe_subcommand]
        view.undo()
        return self

    def dispatch(self, msg):
        # we are changing how this works, because we need to dispatch subcommands as well
        msg.view.skip_string(msg.prefix + self.qualified_name)
        # we will reset the view after we figure out if we are dispatching any subcommands or not.
        msg.view.skip_ws()
        if msg.view.eof:
            return Command.dispatch(self, msg)

        possible_command = msg.view.get_word()  # we dont do a quoted word here, cause who *quotes* a command??
        if possible_command in self.all_commands:
            # we found a subcommand
            self.all_commands[possible_command].dispatch(msg)
            return
        else:
            if self.dispatch_without_command:
                Command.dispatch(self, msg)
                return


def command(name=None, cls=None, **kwargs):
    if cls is None:
        cls = Command

    def deco(func):
        if isinstance(func, Command):
            raise TypeError("already a command or group")
        _name = name
        if _name is None:
            _name = func.__name__
        ret = cls(func, name=_name, **kwargs)
        return ret

    return deco


def group(name=None, cls=None, **kwargs):
    if cls is None:
        cls = Group

    def deco(func):
        if isinstance(func, Command):
            raise TypeError("already a command or group")
        _name = name
        if _name is None:
            _name = func.__name__
        ret = cls(func, name=_name, **kwargs)
        return ret

    return deco


def user_cooldown(per, rate=1):
    """
    adds a per-user cooldown to a Command.
    if the cooldown is triggered, CommandOnUserCooldown is raised, sent to Bot.on_command_error, and
    the local error handler.

    params
    -------
        per: :class:`Union`[:class:`int`, :class:`float`], the amount of time to wait when a cooldown has been triggered.
        rate: :class:`int`, the amount of times the command can be used before triggering. defaults to 1
    """

    def deco(func):
        if isinstance(func, Command):
            func._coolers.append(
                CooldownMapping(Cooldown(rate, per, BucketType.user)))
        else:
            try:
                func.__coolers__.append(Cooldown(rate, per, BucketType.user))
            except AttributeError:
                func.__coolers__ = [Cooldown(rate, per, BucketType.user)]
        return func

    return deco


def global_cooldown(per, rate=1):
    """
    adds a global cooldown to a Command.
    if the cooldown is triggered, CommandOnGlobalCooldown is raised.

    params
    -------
        per: :class:`Union`[:class:`int`, :class:`float`], the amount of time to wait when a cooldown has been triggered.
        rate: :class:`int`, the amount of times the command can be used before triggering. defaults to 1
    """

    def deco(func):
        if isinstance(func, Command):
            func._coolers.append(
                CooldownMapping(Cooldown(rate, per, BucketType.all)))
        else:
            try:
                func.__coolers__.append(Cooldown(rate, per, BucketType.all))
            except AttributeError:
                func.__coolers__ = [Cooldown(rate, per, BucketType.all)]
        return func

    return deco


# we import this at the bottom to avoid a circular import
from .node import Node
