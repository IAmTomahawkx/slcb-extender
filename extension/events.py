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

Thanks to Ocgineer for his EventReciever.dll and boilerplate
"""
from .bin.StreamlabsEventReciever import StreamlabsEventClient
import logging

logger = logging.getLogger(__name__)

class EventsNode:
    def __init__(self, bot):
        self._bot = bot

    def on_init(self, bot):
        self.receiver = StreamlabsEventClient()
        self.receiver.StreamlabsSocketConnected += self.on_event_connect
        self.receiver.StreamlabsSocketDisconnected += self.on_event_disconnect
        self.receiver.StreamlabsSocketEvent += self.on_event_receive
        if bot.settings.StreamlabsEventToken is not None:
           self.receiver.Connect(bot.settings.StreamlabsEventToken)
        bot.add_listener(self.on_reload_settings)
        bot.add_listener(self.on_unload)

    def on_unload(self):
        if self.receiver and self.receiver.IsConnected:
            self.receiver.Disconnect()
            self.receiver = None

    def on_reload_settings(self, settings):
        if self.reciever.IsConnected:
            self.receiver.Disconnect()

        # Connect if token has been entered and EventReceiver is not connected
        # This can then connect without having to reload the script
        if not self.receiver.IsConnected and settings.StreamlabsEventToken:
            self.receiver.Connect(settings.StreamlabsEventToken)

    def on_event_connect(self, sender, args):
        logger.debug("Streamlabs event receiver connected.")
        self._bot.dispatch("event_connect")

    def on_event_disconnect(self, sender, args):
        logger.debug("Streamlabs event receiver disconnected")
        self._bot.dispatch("event_disconnect")

    def on_event_receive(self, sender, args):
        # Just grab the all data in from the event
        evntdata = args.Data

        # Check if it contains data and for what streaming service it is
        if evntdata and evntdata.For == "twitch_account":

            # This is an Twitch follow event
            if evntdata.Type == "follow":
                # Events can come in bulk so it is in a list, iterate over it.
                for message in evntdata.Message:
                    user = self._bot.get_user(message.Name)
                    self._bot.dispatch("follow", user)

            # This is a Twitch cheer event
            elif evntdata.Type == "bits":
                for message in evntdata.Message:
                    user = self._bot.get_user(message.Name)
                    self._bot.dispatch("cheer", user, message.Amount, message.Message)

            # This is a Twitch subscription event
            elif evntdata.Type == "subscription":
                for message in evntdata.Message:
                    if message.Gifter:
                        user = self._bot.get_user(message.Name)
                        gifter = self._bot.get_user(message.Gifter)
                        self._bot.dispatch("gift_sub", user, gifter)
                    elif message.StreakMonths:  # Is a nullable int in .NET can check if it is not None
                        user = self._bot.get_user(message.Name)
                        self._bot.dispatch("streak_sub", user, message.Months, message.StreakMonths)
                    elif message.Months > 1:  # Reliable way to to detect resub, as SubType is can vary with testing/real but also can contain subgift value
                        user = self._bot.get_user(message.Name)
                        self._bot.dispatch("resub", user, message.Months)
                    else:
                        user = self._bot.get_user(message.Name)
                        self._bot.dispatch("sub", user)

        elif evntdata and evntdata.For == "streamlabs":
            # This is a streamlabs donation event
            if evntdata.Type == "donation":
                for message in evntdata.Message:
                    user = self._bot.get_user(message.Name)
                    self._bot.dispatch("donation", user, float(message.Amount), message.Currency)
        self._bot.dispatch("event_receive", sender, args.Data)
