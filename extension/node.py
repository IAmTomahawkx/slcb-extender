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
import sys

__all__ = ("Node",)

def wrapped_listener(node, bot, function):
    def wrapped(*args, **kwargs):
        try:
            function(node, *args, **kwargs)
        except Exception as e:
            bot.dispatch("error", e, sys.exc_info()[2])
            node.node_error(e, sys.exc_info()[2])

    wrapped.__flag = function.__flag
    return wrapped

class Node(GroupMapping):
    def __init__(self, *args, **kwargs):
        GroupMapping.__init__(self, *args, **kwargs)
        self.__node_name__ = kwargs.get("name", self.__class__.__name__)
        self.__listeners__ = self.__dict__.get("__listeners__", [])

    @property
    def name(self):
        return self.__node_name__

    def node_error(self, error, traceback):
        pass

    @classmethod
    def listener(cls, event=None):
        """
        a decorator to indicate the function as an event listener

        :param event: str: the event to listen for. defaults to the function name
        :return:
        """
        def inner(func):
            func.__flag = event or func.__name__
            if not hasattr(cls, "__listeners__"):
                cls.__listeners__ = [func]
            else:
                cls.__listeners__.append(func)

        return inner

    def _attach(self, bot):
        self._listeners = [wrapped_listener(self, bot, func) for func in self.__listeners__]
        for fun in dir(self):
            fun = getattr(self, fun)
            if isinstance(fun, Command):
                fun.node = self
                fun._attach(bot)
                if not fun.parent:
                    if fun.qualified_name in self.all_commands:
                        raise CommandExists("the command {} is already registered in this node ({})".format(fun.qualified_name, self.name))

                    self.all_commands[fun.qualified_name] = fun

        return self

    def _detach(self, bot):
        pass
