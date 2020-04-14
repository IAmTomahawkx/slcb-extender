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
import collections
import logging
import json
import datetime
import time
import sys
import clr
import re
import traceback
import random
import os

from .errors import *
from .abc import *
from .abc import BotBase
from .message import Message
from .commands import *
from .settings import Settings
from .debugger import Debug
from .node import Node


__all__ = [
    "Bot"
]

scriptdir = os.path.dirname(os.path.dirname(__file__))
reUserNotice = re.compile(r"(?:^(?:@(?P<irctags>[^\ ]*)\ )?:tmi\.twitch\.tv\ USERNOTICE)")
logger = logging.getLogger(__name__)

clr.AddReferenceToFileAndPath(os.path.join(os.path.dirname(__file__), "bin", "StreamlabsEventReceiver.dll"))

from .events import EventsNode

class Bot(GroupMapping, BotBase):
    def __init__(self, prefix="!", client_id=None, settings=Settings, **kwargs):
        self.__parent = None
        self.prefix = prefix
        self.__commands = {}
        self.__nodes = {}
        self.__listeners = {"on_send_message": [self._on_send_message], "on_command_error": [self.on_command_error], "on_error":
            [self.on_error], "on_parse": [self.parse], "on_message": [self.on_message]}

        self._parser = None
        self.__script_globals = {}
        self._do_parameters = kwargs.get("do_parameters", True)
        self.settings = settings()

        # i dont know the platform until the first data event comes through
        # so just set it to `None` for now
        self._platform = None
        self._scheduled_events = []
        GroupMapping.__init__(self, **kwargs)

        # no, this is not a mistake. we do this because when a command is registered, GroupMapping passes self._bot
        # to the command.
        self._bot = self

        self.currency_name = ""
        self.random = random.WichmannHill()
        self.stream = self.get_channel(Platforms.twitch) # this works, as all the streaming channels are the same.
        self.discord = self.get_channel(Platforms.discord)
        self._live_dt = None
        self._api = BrowserWindow(self, time.time())
        self._events = EventsNode(self)

        if kwargs.get("enable_debug", False):
            self._debug = True
            self.add_node(Debug(self))

        else:
            self._debug = False

        self.client_id = client_id

    @property
    def parent(self):
        """
        returns the Parent object given by the bot
        """
        return self.__parent

    @property
    def platform(self):
        """
        gives the platform the bot is currently on. this will be an enum member of :ref:`~Platform`
        :return:
        """
        return self._platform

    @property
    def nodes(self):
        return self.__nodes

    def __init(self):
        """
        this will be injected into your script, and will become *Init*.
        Use the on_init event to load things on initialization
        """
        self.__parent = self.__script_globals['Parent']
        self.currency_name = self.parent.GetCurrencyName()
        if self.live:
            self._live_dt = datetime.datetime.now()
        self._events.on_init()
        self.dispatch("init")

    def unload(self):
        """
        this will *not* be injected into your script, however it **must** be called from inside `Unload`!
        """
        self._events.on_unload()
        self.dispatch("unload")

    def __tick(self):
        """
        this will be injected into your script, and will become `Tick`.
        Use the on_tick event to load things on initialization
        """
        if self.live and self._live_dt is None:
            self._live_dt = datetime.datetime.now()

        if not self.live and self._live_dt is not None:
            self._live_dt = None

        dispatched = 0
        for event in self._scheduled_events:
            if event.should_dispatch():
                dispatched += 1
                event.dispatch()
                self._scheduled_events.remove(event)

                if dispatched > 3:
                    break

            else:
                self.debug("delaying event {0}".format(repr(event)))

        self.dispatch("tick")

    def __reload_settings(self, payload):
        """
        this will be injected into your script, and will become *ReloadSettings*.
        Use the on_reload_settings event to load things on initialization
        
        Parameters
        -----------
        payload: the json string provided by the streamlabs chatbot.
        """
        formatted = json.loads(payload)
        self.settings.reload(payload)
        self._events.on_reload_settings()
        for i in self.__commands.values():
            i.namer(self)

        self.dispatch("reload_settings", formatted)

    def __execute(self, data):
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
            return

        else:
            self.dispatch("raw_receive", data.RawData)

        if data.IsFromTwitch():
            # the raid event. thanks to Kruiser8 for the regex
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
        globs['Init'] = self.__init
        globs['Execute'] = self.__execute
        globs['Tick'] = self.__tick
        globs['ReloadSettings'] = self.__reload_settings


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

        if flag in self.__listeners:
            self.__listeners[flag].append(func)
        else:
            self.__listeners[flag] = [func]

        return func

    def listen(self, flag=None):
        """
        decorator to add a listener to an event
        :param flag: Optional[str] the event to listen to. defaults to the function name
        :return: Function
        """

        def inner(func):
            self._inject_to_globals(func)
            self.add_listener(func, flag or func.__name__)
            return func

        return inner

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

    def _on_send_message(self, e, location=None, content=None, message=None, highlight=False, target=None):
        if target is not None and (location.id is Platforms.discord or location.id is Platforms.twitch):
            self._dm_parse_and_send(target, content, message, True)
            return

        self._parse_and_send(location, content, message, highlight=highlight)

    def schedule_event(self, flag, delay=0.0, *args, **data):
        """
        internal function to schedule events to be delayed until a later time
        """
        event = Event(self, delay, flag, *args, **data)
        self._scheduled_events.append(event)

    def dispatch(self, flag, *args, **kwargs):
        """
        internal function to dispatch events and listeners
        """
        if flag == "tick":
            self._inner_dispatch(flag, *args, **kwargs) # delaying tick dont work so well...

        else:
            #self.debug("scheduling event on_" + flag)
            if kwargs.get("delay"):
                del kwargs['delay']

            self.schedule_event(flag, 0, *args, **kwargs)

    def _inner_dispatch(self, flag, *args, **kwargs):
        flag = "on_"+flag
        if flag != "on_tick":
            #self.debug("dispatching event: " + flag)
            pass

        if flag in self.__listeners:
            for listener in self.__listeners[flag]:
                self._actual_dispatch(listener, *args, **kwargs)

        for node in self.__nodes.values():
            for listener in node._listeners:
                if listener.__flag == flag:
                    listener(*args, **kwargs)

    def _actual_dispatch(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            self._inner_dispatch("error", e, sys.exc_info()[2]) # give the traceback here, in case there's another error before the handler is called

    def dispatch_command(self, data):
        msg = self.get_message(data)

        if not msg.valid:
            return

        msg.command.dispatch(msg)
    
    def get_message(self, data):
        chan = self.get_channel(self._platform if not data.IsFromDiscord() else Platforms.discord)
        msg = Message(self, data.User, data.UserName, data.Message, chan, data)
        return msg

    def on_command_error(self, msg, exception, tb):
        msg.reply("error! " + exception.message)
        v = traceback.format_exception(type(exception), exception, tb)
        v = "".join(v)
        logger.error(v)
        self.log(v)

    def on_error(self, error, tb):
        v = traceback.format_exception(type(error), error, tb)
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
        return invoked

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
            self.dispatch("error", e, sys.exc_info()[2])

            parsed_message = content
        self._send(channel, parsed_message, highlight=highlight)

    def _dm_parse_and_send(self, user, content, msg, discord=False):
        if not discord and self._platform != Platforms.twitch:
            logger.warning("attempted to whisper on platform %s" % Platforms.sources[self._platform])
            raise CannotWhisperOnPlatform
        try:
            processed = self.parse(msg, content)
        except Exception as e:
            self.dispatch("error", e, sys.exc_info()[2])
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

    def add_node(self, node):
        """
        wip, do not invoke this
        """
        if not isinstance(node, Node):
            raise TypeError("node must be a subclass of extension.Node, not " + node.__class__.__name__)

        node._attach(self)
        for name in node.all_commands:
            if name in self.all_commands:
                raise CommandExists("the command '{}' already exists".format(name))

        self.all_commands.update(node.all_commands)
        self.__nodes[node.name] = node

    def get_node(self, node):
        """
        wip, do not invoke this
        """
        return self.__nodes.get(node)

    def remove_node(self, node):
        """
        wip, do not invoke this
        """
        tree = self.__nodes.pop(node, None)
        if not tree:
            raise TreeNotFound("the node '{}' was not found".format(node))

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
        return self.__parent.GetViewerList() #type: list
    
    @property
    def active_viewers(self):
        return self.__parent.GetActiveViewers()
    
    def get_random_viewer(self):
        return self.__parent.GetRandomActiveViewer()
    
    def log(self, *data):
        rp = " ".join([str(x) for x in data])
        self.parent.Log(self.__script_globals['ScriptName'], rp)

    def debug(self, *data):
        if not self._debug:
            return

        self.log(*data)
    
    def play(self, fp, volume=100):
        self.__parent.PlaySound(fp, round(volume/100, 1))

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
        return json.loads(self.__parent.PostRequest(target, headers or {}, dict(kwargs)))
    
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
            return
        self._api.vip(user)


class BrowserWindow:
    def __init__(self, bot, startup):
        self.bot = bot
        self.startup = startup
        self.ready = False

    def Show(self):
        self.form.Show()

    def setup(self):
        if time.time() - self.startup < 30:
            raise KeyboardInterrupt
        self.ready = True
        import System.Windows
        from CefSharp.Wpf import ChromiumWebBrowser
        self.form = System.Windows.Window()
        c = self.bot.parent.GetType().Assembly.AnkhBotR2.Helpers.Com.TwitchChatCom
        self.tcom = c(ChromiumWebBrowser())
        self.browser = self.tcom.Browser
        self.form.Content = self.browser

    def runfunc(self, func):
        if not self.ready:
            def coro():
                try:
                    self.setup()
                except:
                    pass
                else:
                    func()

            return self.run_efsharp_thread(coro)
        else:
            return self.run_efsharp_thread(func)

    def send_msg_as_caster(self, msg):
        return self.runfunc(lambda: self.tcom.JSSendCommand(str(msg), ""))

    def vip(self, user):
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

    def run_efsharp_thread(self, runner):
        from System.Threading import Thread, ThreadStart, ApartmentState
        thread = Thread(ThreadStart(runner))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        return thread
