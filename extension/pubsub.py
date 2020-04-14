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
from TwitchLib.PubSub import TwitchPubSub
from .node import Node
import json

class PubSubListener(Node):
    def __init__(self, bot):
        self.bot = bot

    @Node.listener()
    def on_init(self):
        if not self.bot.settings.TwitchApiUsername and self.bot.client_id:
            self.connection = None
        else:
            self.initialize()

    def initialize(self):
        self.connection = TwitchPubSub()
        self.connection.OnPubSubServiceConnected += self.on_pubsub_connect
        self.connection.OnRewarRedeem += self.on_pubsub_redeem
        self.connection.Connect()

    @Node.listener()
    def on_settings_reload(self, *_):
        if self.connection is not None:
            self.connection.Disconnect()

        if self.bot.settings.TwitchApiUsername and self.bot.client_id:
            self.initialize()

    def on_pubsub_connect(self, *_):
        self.bot.dispatch("pubsub_connect")
        headers = {'Client-ID': self.bot.client_id}
        result = self.bot.api_get("https://api.twitch.tv/helix/users?login=" + self.bot.settings.TwitchApiUsername, headers)
        user = json.loads(result["response"])
        id = user["data"][0]["id"]

        self.connection.ListenToRewards(id)
        self.connection.SendTopics()

    def on_pubsub_redeem(self, sender, data):
        self.bot.dispatch("pubsub_redeem", data.RewardTitle)

