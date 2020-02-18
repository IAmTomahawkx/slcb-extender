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
import re
import traceback
import random
import os
from .errors import *
from .abc import *
from .abc import BotBase
from .message import Message
from .tree import *
from .commands import *
from .settings import Settings
import collections
import logging
import json
import datetime
import time
import clr

__all__ = [
    "Bot"
]

scriptdir = os.path.dirname(os.path.dirname(__file__))
reUserNotice = re.compile(r"(?:^(?:@(?P<irctags>[^\ ]*)\ )?:tmi\.twitch\.tv\ USERNOTICE)")
logger = logging.getLogger(__name__)


# clr.AddReference("System.Windows.Forms")
# clr.AddReferenceByPartialName("PresentationFramework")
# clr.AddReferenceByPartialName("PresentationCore")
# clr.AddReferenceToFile('CefSharp.Wpf.dll')
# clr.AddReference('System.Threading')
# from System.Windows.Forms.MessageBox import Show
# msg = lambda obj: Show(str(obj))

class Bot(GroupMapping, BotBase):
    def __init__(self, prefix="!", push_data_errors=True, settings=Settings, **kwargs):
        self.__parent = None
        self.prefix = prefix
        self.__commands = {}
        self.__trees = {}
        self.__listeners = []
        self.__events = {"on_send_message": self._on_send_message, "on_command_error": self.on_command_error,
                         "on_error":
                             self.on_error, "on_parse": self.parse, "on_message": self.on_message}

        self._push_platform_errors = push_data_errors
        self._parser = None
        self.__script_globals = {}
        self._do_parameters = kwargs.get("do_parameters", True)
        self.handle_errors = kwargs.get("handle_errors", True)
        self.settings = settings()

        # i dont know the platform until the first data event comes through
        # so just set it to `None` for now
        self._platform = None
        self._scheduled_events = []
        GroupMapping.__init__(self, **kwargs)

        # no, this is not a mistake. we do this because when a command is registered, GroupMapping passes self._bot
        # to the command.
        self._bot = self

        self.running = True
        self.currency_name = ""
        self.random = random.WichmannHill()
        self.stream = self.get_channel(Platforms.twitch)  # this works, as all the streaming channels are the same.
        self.discord = self.get_channel(Platforms.discord)
        self._live_dt = None
        self._api = API(self, time.time())

    def init(self):
        """
        this will be injected into your script, and will become *Init*.
        Use the on_init event to load things on initialization
        """
        self.__parent = self.__script_globals['Parent']
        self.currency_name = self.parent.GetCurrencyName()
        if self.live:
            self._live_dt = datetime.datetime.now()
        self.dispatch("init")

    @property
    def parent(self):
        """
        returns the Parent object given by the bot
        """
        return self.__parent

    def unload(self):
        """
        this will be injected into your script, and will become *Unload*.
        Use the on_unload event to load things on initialization
        """
        self.dispatch("unload")

    def tick(self):
        """
        this will be injected into your script, and will become *Tick*.
        Use the on_tick event to load things on initialization
        """
        if self.live and self._live_dt is None:
            self._live_dt = datetime.datetime.now()
        if not self.live and self._live_dt is not None:
            self._live_dt = None
        for event in self._scheduled_events:
            if event.should_dispatch():
                event.dispatch()
                self._scheduled_events.remove(event)
        self.dispatch("tick")

    def reload_settings(self, payload):
        """
        this will be injected into your script, and will become *ReloadSettings*.
        Use the on_reload_settings event to load things on initialization

        Parameters
        -----------
        payload: the json string provided by the streamlabs chatbot.
        """
        formatted = json.loads(payload)
        self.settings.reload(payload)
        for i in self.__commands.values():
            i.namer(self)
        self.dispatch("reload_settings", formatted)

    def execute(self, data):
        """
        this will be injected into your script, and will become *Execute*.
        Use the on_message event to load things on initialization

        this is where all commands are fired from, and events such as :meth:`on_host` are fired from.
        with that in mind, do note that this should be called for *all* events, not just chat messages.

        Parameters
        -----------
        data: the data object passed to Execute by the streamlabs chatbot.

        Raises
        -------
        Any error raised while attempting to run commands/events will be passed to the error handlers.
        note that any exceptions raised by the error handlers will not be handled by the bot in any way.
        anything propagating out of this function has been raised by the error handler.

        Returns
        ---------
        None
        """
        if self._platform is None:
            if data.IsFromTwitch():
                self._platform = Platforms.twitch
            elif data.IsFromMixer():
                self._platform = Platforms.mixer
            elif data.IsFromYoutube():
                self._platform = Platforms.youtube

        if data.IsChatMessage():
            self.dispatch("message", data)

        if data.IsFromTwitch():
            # the raid event. thanks to Kruiser8 for the regexes
            usernotice = reUserNotice.search(data.RawData)
            if usernotice:
                tags = dict(re.findall(r"([^=]+)=([^;]*)(?:;|$)", usernotice.group("irctags")))
                id = tags['msg-id']
                if id == 'raid':
                    displayName = tags['msg-param-displayName']
                    viewerCount = tags['msg-param-viewerCount']
                    self.dispatch("raid", displayName, viewerCount)

    def _inject_to_globals(self, func):
        if "Init" in func.__globals__:
            return
        self.__script_globals = func.__globals__
        globs = func.__globals__
        globs['Init'] = self.init
        globs['Execute'] = self.execute
        globs['Tick'] = self.tick
        globs['ReloadSettings'] = self.reload_settings

    def listen(self, flag=None):
        """
        a decorator shortcut to :meth:`~add_listener`

        Parameters
        -----------
        flag: the event to listen to. defaults to the function name
        """

        def deco(func):
            self._inject_to_globals(func)
            return self.add_listener(func)

        return deco

    def add_listener(self, func, flag=None):
        """
        adds an event listener to the bot.
        listeners act like events, but there can be unlimited amount of listeners.

        Parameters
        -----------
        func: the function to use as a listener
        flag: the event to listen to. defaults to the function name
        """
        if not flag:
            flag = func.__name__
        if flag == "on_command_error" or flag == "on_error":
            raise BotException("cannot add listeners to 'command_error' and 'error' events")
        func.__flag = flag
        self.__listeners.append(func)
        return func

    def event(self, flag=None):
        """
        a decorator to add an event flag internally

        Parameters
        -----------
        flag: optional flag parameter. defaults to the function name.
        """

        def deco(func):
            self._inject_to_globals(func)
            _flag = flag
            if not _flag:
                _flag = func.__name__
            self.__events[_flag] = func
            func.__flag = _flag
            return func

        return deco

    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.GroupMapping.add_command`.
        """

        def decorator(func):
            self._inject_to_globals(func)
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
            self._inject_to_globals(func)
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def get_event_caller(self, flag):
        """
        internal function to get the decorated event function
        """
        return self.__events.get("on_" + flag)

    def _on_send_message(self, e, location=None, content=None, message=None, highlight=False, target=None):
        if target is not None and (location.id is Platforms.discord or location.id is Platforms.twitch):
            self._dm_parse_and_send(target, content, message, True)
            return
        self._parse_and_send(location, content, message, highlight=highlight)

    def schedule_event(self, flag, delay=0.0, **data):
        """
        internal function to schedule events to be delayed until a later time
        """
        event = Event(self, delay, flag, **data)
        if delay < 1:
            # dispatch the event now, instead of adding it to a queue
            return event.dispatch()
        self._scheduled_events.append(event)

    def dispatch(self, flag, *args, **kwargs):
        """
        internal function to dispatch event listener
        """
        try:
            self._dispatch_event(flag, *args, **kwargs)
        except Exception as e:
            v = self.get_event_caller("error")
            if not v:
                return
            v(e)

    def _dispatch_event(self, flag, *args, **kwargs):
        flag = "on_" + flag
        logger.debug("dispatching event: " + flag)
        e = self.__events.get(flag, None)
        if e:
            self._actual_dispatch(e, *args, **kwargs)
        for tree in self.__trees:
            tree._dispatch_listeners(flag, *args, **kwargs)
        for listener in self.__listeners:
            if listener.__flag == flag:
                self._actual_dispatch(listener, *args, **kwargs)

    def _actual_dispatch(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            ignore_me = self.__events.get("on_error")
            ignore_me(e)  # this is the error handler dispatch. this line is not part of your problem
        # if the handler raises an exception, the above line can be seen in the traceback.
        # so we need to make it really clear that this line is not part of the problem.
        # or else i get yelled at that i made a mistake :(

    def dispatch_command(self, data):
        msg = self.get_message(data)
        try:
            if not msg.invoked_prefix or msg.command is None:
                # not our prefix, ignore this message.
                return
            msg.command.dispatch(msg)
        except CommandError as e:
            h = self.get_event_caller("command_error")
            h(msg, e)
        except Exception as e:
            v = ExceptionCaught("Command {0}".format(msg.command.qualified_name), e)
            h = self.get_event_caller("command_error")
            h(msg, v)

    def get_message(self, data):
        chan = self.get_channel(self._platform if not data.IsFromDiscord() else Platforms.discord)
        msg = Message(self, data.User, data.UserName, data.Message, chan, data)
        return msg

    def on_command_error(self, msg, exception):
        msg.reply("error! " + exception.message)
        v = traceback.format_exc()
        logger.exception(v)

    def on_error(self, exception):
        v = traceback.format_exc()
        self.log(v)

    def on_message(self, data):
        self.dispatch_command(data)

    def get_prefix(self, msg):
        """
        returns the given prefixes, and the invoked prefixes for a given message.

        Parameters
        ------------
        msg: the :ref:`Message` object for the given message.
        """
        ret = self.prefix
        try:
            ret = list(ret)
        except TypeError:
            # It's possible that a generator raised this exception.  Don't
            # replace it with our own error if that's the case.
            if isinstance(ret, collections.Iterable):
                raise

            raise TypeError(
                "command_prefix must be plain string or iterable of strings, not {}".format(ret.__class__.__name__))

        if not ret:
            raise ValueError("Iterable command_prefix must contain at least one prefix")

        invoked = None
        for prefix in ret:
            if msg.content.startswith(prefix):
                invoked = prefix
                break
        return ret, invoked

    def _schedule_message(self, content, delay, location, msg, highlight=False, target=None):
        """
        schedules a message to be sent at a later date. if the delay if 0, send it right away.

        Parameters
        ------------
        content: the message to be sent

        delay: the delay to when the message will be send

        location: where to send the message

        highlight: whether or not to prefix the message with **/me** . twitch only

        target: the person to send the message, only used for dm messages.
        """
        event = Event(self, delay, "send_message", location=location, content=content, message=msg, highlight=highlight,
                      target=target)
        if delay <= 0:
            # do not schedule the event, just run it.
            event.dispatch()
            return
        self._scheduled_events.append(event)

    def parse(self, msg, content):
        """
        called every time a message is sent from the bot. default implementation does nothing
        useful for $parameters

        Parameters
        -----------
        msg: the :class:`Message` object. may be None.
        content: the :class:`str` to be parsed.
        """
        return content

    def _parse_and_send(self, channel, content, message, highlight=False):
        try:
            parsed_message = self.parse(message, content)
        except Exception as e:
            ignore_me = self.__events.get("error")
            ignore_me(e)  # this is the error handler dispatch. this line is not part of your problem
            # if the handler raises an exception, the above line can be seen in the traceback.
            # so we need to make it really clear that this line is not part of the problem.
            # or else i get yelled at that i made a mistake :(

            parsed_message = content
        self._send(channel, parsed_message)

    def _dm_parse_and_send(self, user, content, msg, discord=False):
        if not discord and self._platform != Platforms.twitch:
            logger.warning("attempted to whisper on platform %s" % Platforms.sources[self._platform])
            if self._push_platform_errors:
                raise CannotWhisperOnPlatform
        try:
            processed = self.parse(msg, content)
        except Exception as e:
            ignore_me = self.__events.get("error")
            ignore_me(e)  # this is the error handler dispatch. this line is not part of your problem
            # if the handler raises an exception, the above line can be seen in the traceback.
            # so we need to make it really clear that this line is not part of the problem.
            # or else i get yelled at that i made a mistake :(
            processed = content
        if discord:

            self.__parent.SendDiscordDM(user, processed)
        else:
            self.__parent.SendStreamWhisper(user, processed)

    def _send(self, channel, content, highlight=False):
        """
        should not be invoked directly
        sends a message to the specified target.
        """
        if self._platform is Platforms.twitch and highlight:
            content = "/me " + content
        if channel.id in Platforms.stream_services:
            self.__parent.SendStreamMessage(content)
        elif channel.id == Platforms.discord:
            self.__parent.SendDiscordMessage(content)

    def add_command(self, command):
        """
        adds a command to the bot.
        """
        command = GroupMapping.add_command(self, command)
        self.__commands[command.name] = command
        # do not add aliases to __commands.

    def add_tree(self, tree):
        """
        wip, do not invoke this
        """
        if not isinstance(tree, Tree):
            raise TypeError("tree must be a subclass of chatbot.Tree, not " + tree.__class__.__name__)
        tree._attach(self)
        for name in tree.all_commands:
            if name in self.all_commands:
                raise CommandExists("the command '{}' already exists".format(name))
        self.all_commands.update(tree.all_commands)
        self.__trees[tree.name] = tree

    def get_tree(self, tree_name):
        """
        wip, do not invoke this
        """
        return self.__trees.get(tree_name)

    def remove_tree(self, tree_name):
        """
        wip, do not invoke this
        """
        tree = self.__trees.get(tree_name)
        if not tree:
            raise TreeNotFound("the tree '{}' was not found".format(tree_name))
        for name in tree.commands:
            if name in self.commands:
                self.remove_command(name)
        tree._detach()

    # ===============
    # Public API
    # ===============

    @property
    def streamer_name(self):
        return str(self.__parent.GetChannelName())

    @property
    def live(self):
        return self.__parent.IsLive()

    @property
    def live_timer(self):
        if not self.live:
            return 0
        return round(time.mktime(datetime.datetime.now().timetuple()) - time.mktime(self._live_dt.timetuple()))

    @property
    def currencyname(self):
        return self.__parent.GetCurrencyName()

    @property
    def viewers(self):
        return self.__parent.GetViewerList()  # type: list

    @property
    def active_viewers(self):
        return self.__parent.GetActiveViewers()

    def get_random_viewer(self):
        return self.__parent.GetRandomActiveViewer()

    def log(self, *data):
        rp = " ".join([str(x) for x in data])
        self.parent.Log(self.__script_globals['ScriptName'], rp)

    def play(self, fp, volume=100):
        self.__parent.PlaySound(fp, round(volume / 100, 1))

    def get_channel(self, platform):
        if isinstance(platform, str):
            platform = Platforms.sources[platform]
        ret = Channel(self, platform)
        return ret

    def get_user(self, id):
        return User(id, self.__parent.GetDisplayName(id), bot=self)

    def broadcast_ws_event(self, event_flag, headers=None, **kwargs):
        return json.loads(self.__parent.BroadcastWSEvent(event_flag, json.dumps(kwargs), headers=headers or {}))

    def api_get(self, target, headers=None):
        v = self.__parent.GetRequest(target, headers or {})
        v = json.loads(v)
        ret = collections.namedtuple("response", list(v.keys()))
        for a, b in v.items():
            setattr(ret, a, b)
        return ret

    def api_post(self, target, headers=None, **kwargs):
        return json.loads(self.__parent.PostRequest(target, headers, dict(kwargs)))

    def mass_add_points(self, items):
        """
        add points to many people at once

        Parameters
        -----------
        items: a list of tuples that contain the :func:`User` and the amount
        """
        for user, amo in items:
            self.__parent.AddPoints(user.id, user.name, amo)
        return list()

    def mass_remove_points(self, items):
        """
        removes points from many people at once

        Parameters
        -----------
        items: a list of tuples that contain the :func:`User` and the amount
        """
        failed = []
        for user, amo in items:
            if not self.__parent.RemovePoints(user.id, user.name, amo):
                failed.append(user)
        return failed

    def purge_user(self, user):
        self._api.purge(user)

    def send_caster_message(self, msg):
        self._api.send_msg_as_caster(msg)

    def set_editor(self, user):
        self._api.editor(user)

    def set_vip(self, user, state):
        if (self.parent.HasPermission(user.id, "VIP", "") and state) or \
                (not self.parent.HasPermission(user.id, "VIP", "") and not state):
            return False
        return self._api.vip(user)


class API:
    def __init__(self, bot, startup):
        self.bot = bot
        self.startup = startup
        self.ready = False

    def Show(self):
        self.form.Show()

    def setup(self):
        if time.time() - self.startup < 0:
            raise ValueError()
        self.ready = True
        import System.Windows
        from CefSharp.Wpf import ChromiumWebBrowser
        self.form = System.Windows.Window()
        c = self.bot.parent.GetType().Assembly.AnkhBotR2.Helpers.Com.TwitchChatCom
        self.tcom = c(ChromiumWebBrowser())
        self.browser = self.tcom.Browser
        self.form.Content = self.browser

    def runfunc(self, func):
        class State:
            # we're just going to ducktype our way through this
            ret = True
        state = State()
        def coro():
            try:
                if not self.ready:
                    self.setup()
                func()
            except Exception as e:
                state.ret = traceback.format_exc()
        return self.run_net_thread(coro, state)

    def send_msg_as_caster(self, msg):
        return self.runfunc(lambda: self.tcom.JSSendCommand(str(msg), ""))

    def vip(self, user, bot=None):
        return self.runfunc(lambda: self.tcom.JSSendCommand("/vip " + user.id, ""))

    def purge(self, user):
        return self.runfunc(lambda: self.tcom.JSPurge(user.id))

    def editor(self, user):
        return self.runfunc(lambda: self.tcom.JSEditor(user.id))

    def regular(self, user):
        return self.runfunc(lambda: self.tcom.JSRegular(user.id))

    def ban(self, user):
        return self.runfunc(lambda: self.tcom.JSBan(user.id))

    def timeout(self, user):
        return self.runfunc(lambda: self.tcom.JSTimeout(user.id))

    def run_net_thread(self, coro, state, block=True):
        from System.Threading import Thread, ThreadStart, ApartmentState
        thread = Thread(ThreadStart(coro))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        if block:
            while thread.IsAlive:
                pass
            thread.Finalize()
            return state.ret
        return thread, state
