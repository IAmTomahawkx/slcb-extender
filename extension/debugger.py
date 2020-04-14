import sys

from .node import Node
from .commands import group
from .checks import check_caster
from .abc import RestOfInput, Optional, User
from .view import StringView
from .errors import *

class Debug(Node):
    def __init__(self, bot):
        Node.__init__(self)
        self.bot = bot

    @group()
    @check_caster()
    def dev(self, msg):
        pass

    @dev.command()
    def su(self, msg, user=User, command=str, text=Optional[RestOfInput]):
        cmd = self.bot.get_command(command)
        if cmd is None:
            return msg.reply("Could not find command {0}".format(command))

        view = StringView(text)
        msg.view = view
        msg.author = user
        msg.command = cmd

        cmd.dispatch(msg)

    @dev.command()
    def sudo(self, msg, command=str, text=Optional[RestOfInput]):
        cmd = self.bot.get_command(command)
        if cmd is None:
            return msg.reply("Could not find command {0}".format(command))

        view = StringView(text)
        msg.view = view
        msg.command = cmd

        try:
            cmd._do_dispatch(msg, run_checks=False)
        except CommandError as e:
            msg.bot.dispatch("command_error", e, sys.exc_info()[2])

        except Exception as e:
            v = ExceptionCaught("Command {0}".format(cmd.qualified_name), e)
            msg.bot.dispatch("command_error", v, sys.exc_info()[2])
