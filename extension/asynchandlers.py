import sys

__all__ = (
    "Future",
)

class Future:
    def __init__(self, bot, flag):
        self._bot = bot
        self._callback = None
        self._complete = False
        self._flag = flag

    @property
    def callback(self):
        return self._callback

    def then(self, callback):
        if not callable(callback):
            raise ValueError("callback is not a callable")

        self._callback = callback

    def wakeup_waiter(self, event, *args, **kwargs):
        if event == "on_" + self._flag:
            self.fire(*args, **kwargs)

    def fire(self, *args, **kwargs):
        try:
            self._callback(*args, **kwargs)
        except Exception as e:
            self._bot.dispatch("error", e, sys.exc_info()[2])
