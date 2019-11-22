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
from .commands import GroupMapping, Command, command, Group, group, _CaseInsensitiveDict, BotBase
from .errors import *
import inspect

__all__ = ["Tree"]


class Tree:
    def __init__(self, *args, **kwargs):
        """
        this function is partially borrowed from rapptz' discord.py command extension library
        """
        self.__cog_name__ = kwargs.pop('name', self.__class__.__name__)
        self.__cog_settings__ = command_attrs = kwargs.pop('command_attrs', {})

        commands = {}
        listeners = {}
        no_bot_cog = 'Commands or listeners must not start with tree_ or bot_ (in method {0.__name__}.{1})'

        for elem, value in self.__dict__.items():
            if elem in commands:
                del commands[elem]
            if elem in listeners:
                del listeners[elem]

            is_static_method = isinstance(value, staticmethod)
            if is_static_method:
                value = value.__func__
            if isinstance(value, Command):
                if is_static_method:
                    raise TypeError('Command in method {0}.{1!r} must not be staticmethod.'.format(None, elem))
                if elem.startswith(('tree_', 'bot_')):
                    raise TypeError(no_bot_cog.format(None, elem))
                commands[elem] = value
                self.add_command(value)
            else:
                try:
                    is_listener = getattr(value, '__cog_listener__')
                except AttributeError:
                    continue
                else:
                    if elem.startswith(('cog_', 'bot_')):
                        raise TypeError(no_bot_cog.format(None, elem))
                    listeners[elem] = value

        self.__cog_commands__ = list(commands.values())

        listeners_as_list = []
        for listener in listeners.values():
            for listener_name in listener.__cog_listener_names__:
                # I use __name__ instead of just storing the value so I can inject
                # the self attribute when the time comes to add them to the bot
                listeners_as_list.append((listener_name, listener.__name__))

        self.__cog_listeners__ = listeners_as_list

        self.__original__kwargs = kwargs.copy()
        case_insensitive = kwargs.get('case_insensitive', False)
        self.all_commands = _CaseInsensitiveDict() if case_insensitive else {}
        self.case_insensitive = case_insensitive

    @property
    def name(self):
        return self.__cog_name__

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
                command._bot = self
        elif self._bot is not None:
            if isinstance(command, Group):
                command._set_bot(self)
            else:
                command._bot = self._bot

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
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def listener(self, flag=None):
        def deco(func):
            func.__cog_listener__ = flag or func.__name__.replace("on_", "")
            return func
        return deco

    def _dispatch_listeners(self, flag, *args, **kwargs):
        for i in self.__cog_listeners__:
            if i.__cog_listener__ == flag:
                try:
                    i(*args, **kwargs)
                except CommandError:
                    raise
                except Exception as e:
                    raise ExceptionCaught(flag, e)

    def _attach(self, bot):
        self.all_commands = bot.all_commands
        self._bot = bot
        for name, func in inspect.getmembers(self, lambda a: not inspect.isroutine(a) and not inspect.ismethod(a)):
            print name, func
            if isinstance(func, Group):
                self.add_command(func)
            elif isinstance(func, Command):
                func.tree = self
                if func.parent is not None: # belongs to a group.
                    continue
                self.add_command(func)

    def _detatch(self, bot):
        for i in self.__cog_commands__:
            self.all_commands.has_key(i.name)
            del self.all_commands[i.name]
