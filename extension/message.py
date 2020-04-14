# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2019 IAmTomahawkx

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
from .errors import *
from .abc import *
import datetime
from .view import StringView

__all__ = ["Message"]

class Message:
    __slots__ = ("__bot", "author", "timestamp", "_content", "_channel", "view", "prefix", "command",
                 "did_fail", "args", "kwargs", "data", "parent")
    def __init__(self, bot, aid, aname, content, channel, data):
        self.data = data
        self.bot = bot
        self.parent = bot.parent
        if not isinstance(aid, User):
            aid = User(aid, aname, bot=bot)
        self.author = aid
        self.rawdata = data.RawData
        self.timestamp = datetime.datetime.now()
        self._content = content
        if not isinstance(channel, Channel):
            channel = Channel(bot, channel)
        self._channel = channel
        self.args = []
        self.kwargs = {}
        self.did_fail = False
        self.view = StringView(content)
        self.command = None
        self.prefix = self.bot.get_prefix(self)
        if not self.prefix:
            return

        self._find_for_dispatch()

    @property
    def valid(self):
        return self.prefix is not None and self.command is not None

    def _find_for_dispatch(self):
        commands = self.bot.all_commands
        self.view.skip_string(self.prefix)
        parent_command = self.view.get_word()
        self.view.skip_ws()

        if parent_command in commands:
            target = commands[parent_command]
            if isinstance(target, Group):
                self.command = target._find_command(self.view)
            else:
                self.command = target

    def invoke(self, command, *args, **kwargs):
        """
        invokes the given Command object with the given arguments
        :param command: a Command object
        :param args: the arguments to pass
        :param kwargs: the keyword arguments to pass
        :return:
        """

    @property
    def content(self):
        return self._content

    @property
    def channel(self):
        return self._channel
    
    def reply(self, content, delay=0.0, highlight=False):
        if delay < 1: # do not allow for delays smaller than 1 second
            self.bot._parse_and_send(self._channel, content, self, highlight=highlight)
        else:
            self.bot._schedule_message(content, delay, self._channel.id, self, highlight)

# we import this at the bottom to avoid a circular import
from .commands import Group, Command
