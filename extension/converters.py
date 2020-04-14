#!python2
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
from . import abc

__all__ = [
    "Converter",
    "IntConverter",
    "StrConverter",
    "BoolConverter",
    "UserConverter"
]

class Converter(object):
    """
    base class for all converters.
    if you wish to make your own converter, it **must** subclass this.
    the actual conversion is done in :meth:`~.convert`, and the output must be returned from that function.
    """
    def __init__(self):
        pass

    def convert(self, msg, param, index):
        """
        where the actual conversion is done.

        Parameters
        -----------
        msg: the :class:`Message` object
        param: the string to be converted

        Returns
        ---------
        whatever your converter returns. by default it returns the input string.
        """
        return param

class IntConverter(Converter):
    def convert(self, msg, param, index):
        try:
            ret = int(round(float(param)))
            return ret
        except Exception:
            raise BadArgument("not an integer: "+param)

class FloatConverter(Converter):
    def convert(self, msg, param, index):
        try:
            return float(param)
        except Exception:
            raise BadArgument("Not a number: "+param)

class StrConverter(Converter):
    pass
    # i'm going to get some angry comments about this...
    # yeah, this exists. basically just to streamline the conversion code.


class BoolConverter(Converter):
    def convert(self, msg, param, index):
        lowered = param.lower()
        if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on', "win"):
            return True
        elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off', "lose"):
            return False
        else:
            raise BadArgument(lowered + ' is not a recognised boolean option')

class UserConverter(Converter):
    def convert(self, msg, param, index):
        # for now, im assuming we are using twitch. i need to figure out how to get a userid from a username
        if msg.bot.platform == abc.Platforms.twitch:
            v = msg.bot.parent.GetDisplayName(param.lower())
            if not v:
                raise ConverterError("Thats not a user!")
            return msg.bot.get_user(v)
