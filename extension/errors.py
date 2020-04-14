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
__all__ = [
    "Error",
    "UnexpectedQuoteError",
    "InvalidEndOfQuotedStringError",
    "ExpectedClosingQuoteError",
    "CannotWhisperOnPlatform",
    "BadArgument",
    "BadUnionArgument",
    "ConversionError",
    "ConverterError",
    "ArgumentParsingError",
    "TooManyArguments",
    "MissingArguments",
    "CannotWhisperOnPlatform",
    "CommandError",
    "CommandOnUserCooldown",
    "CommandOnCooldown",
    "CommandOnGlobalCooldown",
    "BotException",
    "EventAlreadyFired",
    "ChecksFailed",
    "NoCommandFound",
    "CommandExists",
    "TreeNotFound",
    "EventNotFound",
    "ExceptionCaught"
]

# ideally all errors will be subclasses of this exception, and even more ideally, CommandError.
class Error(Exception):
    message = None
    def __init__(self, message=""):
        Exception.__init__(self, self.message or message)
        self.message = self.message or message

class TreeNotFound(Error):
    pass

class CommandError(Error):
    pass

class UserInputError(CommandError):
    pass

class QuotingError(UserInputError):
    pass

class UnexpectedQuoteError(QuotingError):
    pass

class InvalidEndOfQuotedStringError(QuotingError):
    pass

class ExpectedClosingQuoteError(QuotingError):
    pass

class ConverterError(UserInputError):
    pass

class ConversionError(ConverterError):
    def __init__(self, msg, converter, original):
        self.converter = converter
        self.original = original
        if not msg:
            msg = self.original.message
        UserInputError.__init__(self, msg)


class BadArgument(UserInputError):
    pass

class BadUnionArgument(BadArgument):
    def __init__(self, union, msg=""):
        self.union = union
        BadArgument.__init__(self, msg)

class ArgumentParsingError(BadArgument):
    pass

class TooManyArguments(UserInputError):
    pass

class MissingArguments(UserInputError):
    def __init__(self, msg, argument):
        self.argument = argument
        UserInputError.__init__(self, msg)

class ChecksFailed(CommandError):
    pass

class NoCommandFound(CommandError):
    def __init__(self, found_what):
        msg = "no command found as "+found_what
        CommandError.__init__(self, msg)

class ExceptionCaught(CommandError):
    def __init__(self, eventtype, original):
        self.original = original
        self.original_msg = original.args[0]
        CommandError.__init__(self, "Exception Caught while running "+eventtype+". original: "+repr(original))

class CommandOnCooldown(CommandError):
    def __init__(self, bucket, retry_after):
        msg = "Command on cooldown. try again in {} seconds".format(retry_after)
        self.retry_after = retry_after
        CommandError.__init__(self, msg)

class CommandOnUserCooldown(CommandOnCooldown):
    pass

class CommandOnGlobalCooldown(CommandOnCooldown):
    pass


class BotException(Error):
    pass

class EventNotFound(BotException):
    def __init__(self, name):
        msg = "The Event '{}' has no Event Attached".format(name)
        BotException.__init__(self, msg)

class CommandExists(Error):
    pass

class EventAlreadyFired(Error):
    pass

class CannotWhisperOnPlatform(Error):
    message = "Cannot Whisper On Platforms Mixer and Youtube"
