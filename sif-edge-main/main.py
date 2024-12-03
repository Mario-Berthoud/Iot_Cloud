from common import EventRequest, Event, BaseFunction, Function, DeleteFunction
from fastapi import FastAPI
from dispatcher import Dispatcher
from scheduler import Scheduler
import builtins
import traceback

app = FastAPI()

dispatcher = Dispatcher()
sch = Scheduler(
    dispatcher=dispatcher.return_event_loop())

dispatcher.wait_loop()
sch.wait_loop()

sch_evt_loop = sch.return_event_loop()


@app.post("/api/event")
def handle_event(evt_req: EventRequest):
    evt = Event(evt_req.name, data=evt_req.data)
    sch_evt_loop.put(evt, True)
    return


@app.post("/api/function")
def register_fn(fn_data: BaseFunction):
    fn = Function(fn_data.name, fn_data.subs, fn_data.url,
                  fn_data.mock, fn_data.method)
    sch.register_fn(fn)
    return


@app.delete("/api/function")
def delete_fn(fn_data: DeleteFunction):
    sch.delete_fn(fn_data.name)
    return


@app.get("/api/status")
def status_fn():
    return sch.status_sch()
