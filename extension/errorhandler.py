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

this is not operational yet.
"""

import os
import io
import codecs
import time
import traceback as _traceback

class Logger(object):
    def __init__(self, file=None):
        if not file:
            fp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "BotLogs.log")
            self.io = codecs.open(self.fp, mode="a", encoding="UTF-8")
        else:
            if isinstance(file, str):
                self.io = codecs.open(file, mode="a", encoding="UTF-8")
            elif isinstance(file, io.IOBase):
                self.io = file
    
    def __del__(self):
        self.io.close()

    def emit(self, msg):
        if not isinstance(msg, str):
            raise ValueError("msg must be str")
        self.io.write(msg)

    def info(self, msg, module="YourScript"):
        msg = "{time}:INFO:{module}:{msg}".format(time=time.ctime(time.time()), module=module, msg=msg)
        self.emit(msg)

    def debug(self, msg, module="YourScript"):
        msg = "{time}:DEBUG:{module}:{msg}".format(time=time.ctime(time.time()), module=module, msg=msg)
        self.emit(msg)

    def critical(self, msg, module="YourScript"):
        msg = "{time}:CRITICAL:{module}:{msg}".format(time=time.ctime(time.time()), module=module, msg=msg)
        self.emit(msg)

    def error(self, msg, module="YourScript"):
        msg = "{time}:ERROR:{module}:{msg}".format(time=time.ctime(time.time()), module=module, msg=msg)
        self.emit(msg)

    def exception(self, msg, module="YourScript"):
        msg = "{time}:EXCEPTION:{module}:{msg}".format(time=time.ctime(time.time()), module=module, msg=msg)
        self.emit(msg)

    def traceback(self, exception=None, tb=None, module="YourScript"):
        if exception and tb:
            formatted = _traceback.format_exception(type(exception), exception, tb)
        else:
            formatted = _traceback.format_exc()
        msg = "TRACEBACK at {time} in module {module}:\n{msg}".format(time=time.ctime(time.time()), module=module, msg=formatted)
        self.emit(msg)
