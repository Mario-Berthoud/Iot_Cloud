##########################
#       MONITORING       #
########################## 

from base import LocalGateway, base_logger, BaseEventFabric, PeriodicTrigger
from sensor_processing import process_sensor_data
import pandas as pd


# Initialize Local Gateway
app = LocalGateway()
base_logger.info("Gateway initiated.")

# Events
class TrainOccupancyModelEvent(BaseEventFabric): # Every ?
    def __init__(self):
        super(TrainOccupancyModelEvent, self).__init__()

    def call(self, *args, **kwargs):
        evt_name = "TrainOccupancyModelEvent"
        data = {"message": "Triggering Ocupancy Model Training"}
        base_logger.info(f"Event generated: {evt_name}")
        return evt_name, data

class CheckEmergencyEvent(BaseEventFabric): # Every minutes?
    def __init__(self):
        super(CheckEmergencyEvent, self).__init__()

    def call(self, *args, **kwargs):
        evt_name = "CheckEmergencyEvent"
        data = {"message": "Emergency Check Event"}
        base_logger.info(f"Event generated: {evt_name}")
        return evt_name, data

class EmergencyEvent(BaseEventFabric):
    def __init__(self, message):
        super(EmergencyEvent, self).__init__()
        self.message = message

    def call(self, *args, **kwargs):
        evt_name = "EmergencyEvent"
        data = {"message": self.message}
        base_logger.info(f"Emergency Event: {evt_name}")
        return evt_name, data

# Emergency Detection Function
async def check_emergency_detection_function():
    base_logger.info("Running emergency detection function...")
    try:
        visit_durations = process_sensor_data(hours=3)  # Process data from sensors

        # Simulated emergency detection logic (replace with actual logic)
        if not visit_durations.empty:
            emergency_message = "Emergency detected: Unusual room duration."
            base_logger.info(emergency_message)

            # Trigger EmergencyEvent
            emergency_event = EmergencyEvent(emergency_message)
            emergency_event()  # Notify Scheduler about the emergency

            base_logger.info("EmergencyEvent triggered and sent to the Scheduler.")
        else:
            base_logger.info("No emergency detected.")
    except Exception as e:
        base_logger.error(f"Error in emergency detection function: {e}")


# Deploy Functions to LocalGateway
app.deploy(check_emergency_detection_function,
           name="check_emergency_detection_function",
           evts="CheckEmergencyEvent",
           method="POST")
base_logger.info("check_emergency_detection_function deployed.")

# Add Triggers
periodicTrainModelTrigger = PeriodicTrigger(TrainOccupancyModelEvent(), duration="5h", wait_time="1m")
periodicCheckEmergencyTrigger = PeriodicTrigger(CheckEmergencyEvent(), duration="10m", wait_time="30s")
base_logger.info("Triggers added: TrainOccupancyModelEvent and CheckEmergencyEvent.")




#####################################
#           EXAMPLE CODE            #
#####################################

# from base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric


# app = LocalGateway()


# async def demo():
#     base_logger.info("HELLO WORLD!!! You did it! :D$$$$$")
#     return


# async def base_fn():
#     """
#     Test example of dynamically deploying another route upon an HTTP request

#     Since this function will be invoked once the `test` event is triggered,
#     the route `/api/other` will be registered at runtime rather than upon 
#     starting the server. Such behavior allows to dynamically create functions
#     that could answer to new events. Be aware that registering two functions
#     with the same name will result in only one route. You can change this
#     behavior by providing the `path` argument.

#     Once this new route is registered, you will see it in the Homecare Hub under
#     SIF Status, which means upon receiving an event (in this case `test`), you
#     will see in the logs of this example the print above.
#     """
#     app.deploy(demo, "demo-fn", "GenEvent")
#     return {"status": 200}

# Deploy a route within this server to be reachable from the SIF scheduler
# it appends the name of the cb to `/api/`. For more, please read the
# documentation for `deploy`
# app.deploy(base_fn, "fn-fabric", "CreateFn")


# evt = ExampleEventFabric()

# tgr = PeriodicTrigger(evt, "30s", "1m")




















































































# from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, ExampleEventFabric
# from fastapi import Request
# from influxdb_client import InfluxDBClient, QueryApi
# import pandas as pd
# from datetime import datetime, timedelta

# # InfluxDB credentials and database details
# INFLUX_TOKEN = "http://192.168.1.132:8086"
# INFLUX_ORG = "wise2024"
# INFLUX_USER = "admin"
# INFLUX_PASS = "secure_influx_iot_user"

# def fetch_data(bucket, measurement, field):

#     buckets = ["1_2_2", "1_2_7", "1_3_10", "1_3_11", "1_3_14", "1_4_12", "1_4_13"]  # List of bucket names

#     with InfluxDBClient(
#         url=INFLUX_TOKEN, 
#         org=INFLUX_ORG, 
#         sername=INFLUX_USER, 
#         password=INFLUX_PASS, 
#         verify_ssl=False) as client:
#             p = {
#                 "_start": timedelta(days=-7),  # "fetch data starting from 7 days ago".
#             }

#             query_api = client.query_api()
#             tables = query_api.query(f'''
#                                     from(bucket: "{bucket}") |> range(start: _start)
#                                     |> filter(fn: (r) => r["_measurement"] == "{measurement}")
#                                     |> filter(fn: (r) => r["_type"] == "{"sensor-value"}")
#                                     |> filter(fn: (r) => r["_field"] == "{field}")
#                                     ''', params=p)
#             for table in tables:
#                 for record in table.records:
#                     base_logger.info(record)
                    
#     return





# def fetch_data():
#     client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
#     query_api = client.query_api()

#     # Query to fetch data
#     query = f'''
#         from(bucket: "{BUCKET}")
#         |> range(start: -7d)  // Last 7 days of data
#         |> filter(fn: (r) => r["_measurement"] == "room_events")
#     '''
#     tables = query_api.query(query)
#     data = []
#     for table in tables:
#         for record in table.records:
#             data.append({
#                 "time": record.get_time(),
#                 "room": record.values.get("room"),
#                 "event": record.values.get("_field"),
#                 "value": record.get_value()
#             })

#     client.close()
#     return pd.DataFrame(data)

# # Fetch data
# data = fetch_data()
# print(data.head())

# def calculate_metrics(data):
#     # Ensure 'time' column is in datetime format
#     data["time"] = pd.to_datetime(data["time"])

#     # Filter only relevant events (e.g., door open/close)
#     open_events = data[data["event"] == "door_open"]
#     close_events = data[data["event"] == "door_close"]

#     # Calculate time spent in each visit
#     open_events = open_events.sort_values(by="time")
#     close_events = close_events.sort_values(by="time")
#     visits = pd.merge_asof(open_events, close_events, on="time", suffixes=("_start", "_end"))
#     visits["duration"] = (visits["time_end"] - visits["time_start"]).dt.total_seconds()

#     # Calculate average duration and visit count per room
#     metrics = visits.groupby("room_start").agg(
#         avg_duration=("duration", "mean"),
#         visit_count=("duration", "count")
#     ).reset_index()

#     # Add seasonality (day of the week and hour of the day)
#     visits["day_of_week"] = visits["time_start"].dt.day_name()
#     visits["hour_of_day"] = visits["time_start"].dt.hour
#     seasonal_metrics = visits.groupby(["room_start", "day_of_week", "hour_of_day"]).agg(
#         avg_duration=("duration", "mean"),
#         visit_count=("duration", "count")
#     ).reset_index()

#     return metrics, seasonal_metrics

# # Process data
# metrics, seasonal_metrics = calculate_metrics(data)
# print("General Metrics:")
# print(metrics)
# print("\nSeasonal Metrics:")
# print(seasonal_metrics)







# from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, ExampleEventFabric
# from fastapi import Request

# class TrainOccupancyModelEvent(BaseEventFabric):
#     def __init__(self):
#         super(TrainOccupancyModelEvent, self).__init__()

#     def call(self, *args, **kwargs):
#         name = "TrainOccupancyModelEvent"
#         data = "Model sent to train"
#         base_logger.info(f"Event generated: {name} information {data}")
#         return name, data
    
# class CheckEmergencyEvent(BaseEventFabric):
#     def __init__(self):
#         super(CheckEmergencyEvent, self).__init__()

#     def call(self, *args, **kwargs):
#         name = "CheckEmergencyEvent"
#         data = "Emergency Check"
#         base_logger.info(f"Event generated: {name} information {data}")
#         return name, data 

# class EmergencyEvent(BaseEventFabric):
#     def __init__(self,message):
#         super(EmergencyEvent, self).__init__()
#         self.message = message

#     def call(self, *args, **kwargs):
#         event = "EmergencyEvent"
#         data = "Emergency Detected"
#         base_logger.info(f"Event generated: {event} with message {self.message}")
#         return event, data, self.message 

# app = LocalGateway()
# base_logger.info("Monitor Gatewau initiated.")


# async def emergency_detection_function(request: Request):
#     base_logger.info("Emergency detection called")
#     data = await request.json()
#     #FUNCTION TO DO
#     return

# # app.deploy(base_fn, "fn-fabric", "CreateFn")
# app.deploy(emergency_detection_function,
#     name="emergency_detection_function",
#     evts="CheckEmergencyEvent",
#     method="POST",
# )
# base_logger.info("Emergency detection function deployed")


# # Function to handle emergency notifications
# async def emergency_notification_function(request: Request):
#     """
#     API endpoint to handle emergency notifications.

#     Args:
#         request (Request): Incoming HTTP request with emergency details.

#     Returns:
#         dict: Status of the operation.
#     """
#     base_logger.info("Emergency notification function triggered.")
#     try:
#         # Parse incoming request
#         data = await request.json()
#         base_logger.info(f"Received emergency data: {json.dumps(data, indent=2)}")





##############

# # Event Class
# class TrainOccupancyModelEvent(BaseEventFabric):
#     def __init__(self):
#        super(TrainOccupancyModelEvent, self).__init__()
#         self.event_type = event_type
#         self.data = data
#         self.timestamp = time.time()

#     def to_dict(self):
#         return {
#             "event_type": self.event_type,
#             "data": self.data,
#             "timestamp": self.timestamp
#         }

##############

# # Event Class
# class TrainOccupancyEvent:
#     def __init__(self, event_type, data):
#         self.event_type = event_type
#         self.data = data
#         self.timestamp = time.time()

#     def to_dict(self):
#         return {
#             "event_type": self.event_type,
#             "data": self.data,
#             "timestamp": self.timestamp
#         }

# # Event Fabric
# class TrainOccupancyModelEventFabric:
#     def create_event(self, event_type, data):
#         # Create and return a new event
#         return TrainOccupancyEvent(event_type, data)

# # Event Trigger
# class TrainOccupancyModelEventTrigger:
#     def __init__(self, scheduler_url):
#         self.scheduler_url = scheduler_url

#     def trigger_event(self, event):
#         # Convert event to JSON and send it to the scheduler
#         try:
#             response = requests.post(self.scheduler_url, json=event.to_dict())
#             print(f"Event sent! Response: {response.status_code}")
#         except Exception as e:
#             print(f"Failed to send event: {e}")





# app = LocalGateway()


# async def demo():
#     base_logger.info("HELLO WORLD!!! You did it! :D")
#     return


# async def base_fn():
#     """
#     Test example of dynamically deploying another route upon an HTTP request

#     Since this function will be invoked once the `test` event is triggered,
#     the route `/api/other` will be registered at runtime rather than upon 
#     starting the server. Such behavior allows to dynamically create functions
#     that could answer to new events. Be aware that registering two functions
#     with the same name will result in only one route. You can change this
#     behavior by providing the `path` argument.

#     Once this new route is registered, you will see it in the Homecare Hub under
#     SIF Status, which means upon receiving an event (in this case `test`), you
#     will see in the logs of this example the print above.
#     """
#     app.deploy(demo, "demo-fn", "GenEvent")
#     return {"status": 200}

# # Deploy a route within this server to be reachable from the SIF scheduler
# # it appends the name of the cb to `/api/`. For more, please read the
# # documentation for `deploy`
# app.deploy(base_fn, "fn-fabric", "CreateFn")


# evt = ExampleEventFabric()

# tgr = PeriodicTrigger(evt, "30s", "1m")
