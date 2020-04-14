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
from . import errors
from .commands import Command
from .abc import Platforms

__all__ = [
    "check",
    "check_moderator",
    "check_subscriber",
    "check_vip",
    "check_editor",
    "check_caster",
    "check_min_rank",
    "check_min_points",
    "check_min_hours",
    "editable_permission",
    "settings_permission"
]

class _Check:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, msg):
        try:
            ret = self.callback(msg)
        except errors.CommandError:
            raise
        except Exception as e:
            raise errors.ExceptionCaught(e, "Check")
        return ret

def check(checker):
    def deco(func):
        if isinstance(func, Command):
            func._checks.append(_Check(checker))
        else:
            try:
                func.__checks__.append(_Check(checker))
            except:
                func.__checks__ = [_Check(checker)]
        return func
    return deco

def check_moderator():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Moderator", ""))

def check_subscriber():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Subscriber", ""))

def check_vip():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "VIP", ""))

def check_editor():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Editor", ""))

def check_regular():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Regular", ""))

def check_caster():
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Caster", ""))

def check_specific_user(username):
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "User_Specific",
                                                          username if isinstance(username, str) else username(msg)))

def check_min_rank(rank):
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Min_Rank",
                                                          rank if isinstance(rank, str) else rank(msg)))

def check_min_points(points):
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Min_Points",
                                                          points if isinstance(points, int) else points(msg)))

def check_min_hours(hours):
    return check(lambda msg: msg.bot.parent.HasPermission(msg.author.id, "Min_Hours",
                                                          hours if isinstance(hours, int) else hours(msg)))
def discord_only():
    return check(lambda msg: msg.channel.id == Platforms.discord)

def stream_only():
    return check(lambda msg: msg.channel.id in Platforms.stream_services)

def settings_permission(permname):
    def predicate(msg):
        perm = getattr(msg.bot.settings, permname)
        extra = getattr(msg.bot.settings, permname+"_info", "")
        return msg.bot.parent.HasPermission(msg.author.id, perm, extra)
    return check(predicate)

def editable_permission(func):
    def predicate(msg):
        level = func(msg)
        if isinstance(level, tuple) and level[0] in ["User_Specific", "Min_Rank", "Min_Points"]:
            v = msg.bot.parent.HasPermission(msg.author.id, level[0], level[1])
        else:
            v = msg.bot.parent.HasPermission(msg.author.id, level, "")
        return v
    return check(predicate)
