import pytz
import urllib3
import logging

from abc import ABC
from typing import Dict, Optional, Any, List
from datetime import datetime
from pydantic import BaseModel

from .status import EventStatus

logger = logging.getLogger("fastapi_cli")

logging.getLogger("requests").setLevel(logging.DEBUG)


class EventRequest(BaseModel):
    name: str
    data: Optional[Dict[Any, Any]] | Optional[Any] = None


class DeleteFunction(BaseModel):
    name: str


class BaseFunction(BaseModel):
    name: str
    subs: List[str]
    url: str
    method: Optional[str] = "GET"
    mock: Optional[bool] = False


class Event(ABC):
    def __init__(self, name: str, data: List[Dict[Any, Any]] | Dict[Any, Any] | Any = None):
        super(Event, self).__init__()
        self.name: str = name
        self.data: List[Dict[Any, Any]] | Dict[Any, Any] = data
        self.status: EventStatus = EventStatus.CREATED
        self.timestamp: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


class Invocation(ABC):
    """
    Abstract class emerging from a function upon fulfilling all event(s)
    requirements.
    """

    def __init__(self, url: str, method: str, mock: bool, ** kwargs):
        super(Invocation, self).__init__()
        self.kwargs = kwargs
        self.url = url
        self.method = method
        self.mock = mock

    def invoke(self):
        try:
            if not self.mock:
                # TODO: Add retries method and provide feedback with function name
                if self.method == "GET":
                    self.kwargs = {}

                res = urllib3.request(self.method, self.url, **self.kwargs)
                if res.status >= 300:
                    logger.warn(
                        f"failure to invoke remote resource because: [{res.reason}]")
                logger.info("invocation has been dispatched")
        except Exception as err:
            logger.error("Failure during invocation...")
            logger.error(err)
        return


class RemoteInvocation(Invocation):
    def __init__(self):
        super(RemoteInvocation, self).__init__()


class Function(ABC):
    """
    Class identifying a function to be called upon an event.

    This class serves as the abstraction of remote requests upon
    the required events being generated. Once the events have
    arrived, the scheduler will generate an invocation from
    the function data, which includes the target's URL and
    correspondg event(s) data.
    """

    def __init__(self, name: str, subs: List[str], ref: str, mock: bool = False, method: str = "GET"):
        super(Function, self).__init__()

        self.name: str = name
        self.ref: str = ref
        self.method: str = method
        self.events: Dict[str, List[Event]] = {}
        self.subs: List[str] = subs
        self.ready: List[List[str]] = []
        self.last_pos = None
        self.mock = mock
        self.last_invoke = None
        self.reset_fn()

    def __repr__(self):
        return pformat(vars(self), indent=4)

    def print(self):
        return f"[{self.name}] -> {self.ref} ? {','.join(self.subs)}"

    def update_event(self, evt: Event) -> bool:
        if evt.name not in self.subs:
            return False
        if len(self.ready) == 0:
            self.events[evt.name] = [evt]
            idx = self.subs.index(evt.name)
            vals = [None for _ in range(len(self.subs))]
            vals[idx] = evt.name
            self.ready.append(vals)
            if None not in self.ready[-1]:
                self.last_pos = 0
                return True
            return False

        for idx, evt_tr in enumerate(self.ready):
            if evt.name in evt_tr:
                if None not in evt_tr:
                    self.last_pos = idx
                evts = [None for _ in range(len(self.subs))]
                evts[self.subs.index(evt.name)] = evt.name
                self.ready.insert(len(self.ready), evts)
                if self.events[evt.name]:
                    self.events[evt.name].insert(len(self.ready), evt)
                else:
                    self.events[evt.name] = [
                        None for _ in range(len(self.ready)+1)]
                    self.events[evt.name][len(self.ready)] = evt

                if None not in self.ready[-1]:
                    self.last_pos = len(self.ready) - 1
                    return True
                return (self.last_pos is not None) or False
            else:
                jdx = self.subs.index(evt.name)
                if self.events[evt.name] is None:
                    self.events[evt.name] = [
                        None for _ in range(len(self.ready))]
                if idx > (len(self.events[evt.name]) - 1):
                    self.events[evt.name].insert(idx, evt)
                else:
                    self.events[evt.name][idx] = evt
                evt_tr[jdx] = evt.name
                if None not in evt_tr:
                    self.last_pos = idx
                    return True
                return False
        return False

    def reset_fn(self):
        if self.last_pos is None:
            for topic in self.subs:
                self.events[topic] = None
            return

        if len(self.ready) > self.last_pos:

            lst = self.ready.pop(self.last_pos)

            for topic in self.subs:
                if len(self.events[topic]) > self.last_pos:
                    self.events[topic].pop(self.last_pos)

            logger.info(
                f"removing {lst} from the ready queue for function {self.name}")
            self.last_pos = None

    def generate_invocation(self) -> Invocation:
        kwargs = dict()
        for k, v in self.events.items():
            vals = dict()
            if v[self.last_pos].data:
                vals["data"] = v[self.last_pos].data
            vals["timestamp"] = v[self.last_pos].timestamp
            kwargs[k] = vals

        inv = Invocation(self.ref, self.method, self.mock, json=kwargs)
        self.reset_fn()
        self.last_invoke = int(datetime.now(
            pytz.timezone("Europe/Berlin")).timestamp()*1000)

        return inv
