from abc import ABC
from threading import Thread
from multiprocessing import Queue

import logging
import common

logger = logging.getLogger("fastapi_cli")


class Dispatcher(ABC):
    def __init__(self):
        super(Dispatcher, self).__init__()

        self.event_loop: Queue[common.Invocation] = Queue()

    def return_event_loop(self) -> "Queue[common.Invocation]":
        """
        Returns the local event loop where the dispatcher listens for
        invocations
        """
        return self.event_loop

    def wait_loop(self) -> Thread:
        dispatcher_thread = Thread(target=self._wait_loop)
        dispatcher_thread.start()
        return dispatcher_thread

    def _wait_loop(self):
        while (event := self.event_loop.get(True)):
            logger.info("event incoming for processing")
            event.invoke()
