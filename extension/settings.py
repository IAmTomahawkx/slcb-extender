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
import os, json, codecs

searchpath = os.path.dirname(os.path.dirname(__file__))

class Settings:
    def __init__(self):
        self._root = None
        self._applied = None
        for f in os.listdir(searchpath):
            if f == "UI_Config.json":
                with codecs.open(os.path.join(searchpath, f), encoding="utf-8") as e:
                    self._root = json.load(e)
                break
        if self._root is None:
            return
        for f in os.listdir(searchpath):
            if f == self._root['output_file']:
                with codecs.open(os.path.join(searchpath, f), encoding="utf-8-sig") as e:
                    self._applied = json.load(e, encoding="utf-8-sig")
                break
        if self._applied is None:
            self._applied = {}
            # no settings exist, use the defaults
            for name, sets in self._root.items():
                if name == "output_file": continue
                self._applied[name] = sets['value']
        self.__dict__.update(self._applied)
        if not hasattr(self, "StreamlabsEventToken"):
            self.StreamlabsEventToken = None

    def reload(self, payload):
        self._applied = json.loads(payload)
        self.__dict__.update(self._applied)

    def save(self):
        with codecs.open(self._root['output_file'], encoding="utf-8-sig") as f:
            json.dump(self._applied, f)
