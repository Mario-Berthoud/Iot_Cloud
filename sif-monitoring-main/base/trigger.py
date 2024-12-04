import time
import schedule
import durationpy

from abc import ABC
from datetime import timedelta
from threading import Thread

from base import BaseEventFabric


def one_shot_cb(cb):
    def handler():
        cb()
        return schedule.CancelJob
    return handler


class Trigger(ABC):
    """
    Child objects of the :class:`Trigger <Trigger>` represent either One-Shot or
    Periodic Triggers for Event Request generation through the :class:`BaseEvent <event.BaseEvent>`
    factory.

    Once any child of this class has been instantiated, it will launch a local
    scheduler, which calls the given callback. The callback must take arguments.

    :param evt_cb: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param duration: frequency of event generation using Golang's time representation, e.g., 1h1m1s
    :param one_shot: indicates if the trigger must be run only once
    :param wait_time: indicates if there must be a delay before scheduling the first executions
    """

    def __init__(self, evt_cb: BaseEventFabric, duration: str = "1s", one_shot: bool = False, wait_time: str = None):
        super(Trigger, self).__init__()

        self.wt = None
        if wait_time is not None:
            self.wt = durationpy.from_str(wait_time)
        else:
            print("Running trigger inmediately...")

        dt: timedelta = durationpy.from_str(duration)
        self.scheduler = schedule.Scheduler()
        fn = self.scheduler.every(dt.total_seconds()).seconds
        if one_shot:
            fn.do(one_shot_cb(evt_cb))
        else:
            fn.do(evt_cb)

        self.thr = Thread(target=self.run)
        self.thr.start()

    def run(self):
        while True:
            if self.wt is not None:
                time.sleep(self.wt.total_seconds())

            self.scheduler.run_pending()
            pending_jobs = self.scheduler.get_jobs()
            if len(pending_jobs) == 0:
                return

            time.sleep(1)


class OneShotTrigger(Trigger):
    """
    Creates a One-Shot Trigger

    :param evt_cb: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param wait_time: indicates if there must be a delay before scheduling the first executions
    """

    def __init__(self, evt_cb: BaseEventFabric, wait_time: str = None):
        super(OneShotTrigger, self).__init__(
            evt_cb, one_shot=True, wait_time=wait_time)


class PeriodicTrigger(Trigger):
    """
    Creates a Periodic Trigger

    :param evt_cb: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param duration: frequency of event generation using Golang's time representation, e.g., 1h1m1s
    :param wait_time: indicates if there must be a delay before scheduling the first executions
    """

    def __init__(self, evt_cb: BaseEventFabric, duration: str, wait_time: str = None):
        super(PeriodicTrigger, self).__init__(
            evt_cb, duration, wait_time=wait_time)