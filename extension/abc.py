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
import datetime
import time
from .errors import *

__all__ = [
    "Platforms",
    "Object",
    "RestOfInput",
    "Event",
    "Channel",
    "User"
]

class Platforms:
    # this totally isnt in order of how i rate each platform as a streaming service
    twitch = 0
    mixer = 1
    youtube = 2
    discord = 3
    stream_services = [0, 1, 2] # i mean, 2 doesnt really belong there, but whatever :P
    sources = {0: "twitch", 1: "mixer", 2: "youtube", 3: "discord"}
    

class Object:
    """
    just your everyday :ref:`Object` that does nothing
    """
    def __init__(self, *args, **kwargs):
        for name in args:
            setattr(self, name, None)
        for a, b in kwargs.items():
            setattr(self, a, b)


class BotBase(object):
    pass

class RestOfInput(object):
    def __init__(self, t=str):
        self.type = t

class Optional(object):
    def __init__(self, t=str):
        self.type = t

class Union(object):
    def __init__(self, *args):
        self.options = args

class Event(object):
    """
    a container to hold scheduled :ref:`events` internally in the :ref:`bot`
    this is not created manually.
    """
    __slots__ = ["_fire_at", "_flag", "_bot", "_payload", "_did_fire"]
    def __init__(self, bot, delay, flag, **payload):
        self._fire_at = time.time() + delay
        self._flag = flag
        self._payload = payload
        self._bot = bot
        self._did_fire = False
    
    def __repr__(self):
        return "<Event Object for flag {} firing at {}>".format(self.flag, time.ctime(float(self)))
    
    def __float__(self):
        return self._fire_at
    
    def __int__(self):
        return round(self._fire_at)
    
    def should_dispatch(self):
        return time.time() >= self._fire_at and not self._did_fire
    
    def dispatch(self):
        if self._did_fire:
            raise EventAlreadyFired("the event with flag {} has already been fired".format(self.flag))
        self._bot._dispatch_event(self._flag, self, **self._payload)
        self._did_fire = True
    
    @property
    def flag(self):
        return self._flag
    
    @property
    def payload(self):
        return self._payload.copy()
        
 
class Channel(object):
    def __init__(self, bot, channelid):
        self.__bot = bot
        self._id = channelid

    @property
    def id(self):
        return self._id
    
    @property
    def source(self):
        return Platforms.sources[self._id]
    
    def send(self, message, highlight=False, delay=0.0):
        """
        send a message to the channel.
        highlight is only used in the case of twitch. it works by prefixing the message with **/me**
        """
        self.__bot._parse_and_send(self, message, None, highlight=highlight)


class User(object):
    name = ""
    id = ""
    _points = 0
    _hours = 0.0
    _rank = ""
    def __init__(self, id, name, **kwargs):
        self.__bot = kwargs.pop("bot", None)
        self.name = name
        self.id = id
        self.permissions = []
        self._find_perms()
        self.highest_permission = self.permissions[0]
    
    @property
    def points(self):
        return self._points
    @property
    def hours(self):
        return self._hours
    @property
    def rank(self):
        return self._rank

    def _find_perms(self):
        parent = self.__bot.parent
        username = self.id
        if parent.HasPermission(username, "Caster", ""):
            self.permissions.append("Caster")
        if parent.HasPermission(username, "Editor", ""):
            self.permissions.append("Editor")
        if parent.HasPermission(username, "Moderator", ""):
            self.permissions.append("Moderator")
        if parent.HasPermission(username, "Subscriber", ""):
            self.permissions.append("Subscriber")
        if parent.HasPermission(username, "Regular", ""):
            self.permissions.append("Regular")
        self.permissions.append("Everyone")
        self._points = parent.GetPoints(username)
        self._rank = parent.GetRank(username)
        self._hours = parent.GetHours(username)
        
    
    def send(self, message, discord):
        if self.bot is None:
            raise BotException("trying to dm user {0}. no bot attached to {1!r}. you need to use bot.get_user() !".format(self.name, self))
        self.__bot._dm_parse_and_send(self.id, message)
    
    def add_points(self, amount):
        """
        adds points to the user
        
        Parameters
        -----------
        amount: an :class:`int`
        """
        if not isinstance(amount, int):
            raise ValueError("add_points expeected an integer, got "+amount.__class__.__name__)
        self.__bot.parent.AddPoints(self.id, self.name, amount)
        self._points += amount
        return self._points
    
    def remove_points(self, amount):
        """
        removes points from a user.
        
        Parameters
        ------------
        amount: an :class:`int`
        
        Raises
        ------------
        :class:`CommandError` if the user does not have enough points
        """
        if not isinstance(amount, int):
            raise ValueError("remove_points expected an integer, got "+amount.__class__.__name__)
        if not self.__bot.parent.RemovePoints(self.id, self.name, amount):
            raise CommandError("{0} does not have enough {1}".format(self.name, self.__bot.currency_name))
        self._points -= amount
        return self._points
    
    def has_permission(self, permission, arg=""):
        return self.__bot.parent.HasPermission(self.id, permission, arg)

