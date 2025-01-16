##########################
#       MONITORING       #
########################## 

from base import LocalGateway, base_logger, BaseEventFabric, PeriodicTrigger

from influxdb_client import InfluxDBClient
from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from minio import Minio
from io import BytesIO
import pandas as pd
import json

# ------------------------------ CONFIGURATION ------------------------------

# InfluxDB credentials and database details
INFLUX_TOKEN = "http://192.168.1.132:8086"
INFLUX_ORG = "wise2024"
INFLUX_USER = "admin"
INFLUX_PASS = "secure_influx_iot_user"

VIZ_COMPONENT_URL = "http://192.168.1.132:9000"
SIF_SCHEDULER = ("SCH_SERVICE_NAME", "192.168.1.132:30032")

# Minio credentials and database details
MINIO_ENDPOINT = "192.168.1.132:9090"
MINIO_ACCESS_KEY = "peUyeVUBhKS7DvpFZgJu"
MINIO_SECRET_KEY = "J5VLWMfzNXBnhrm1kKHmO7DRbnU5XzqUO1iKWJfi"
MINIO_BUCKET = "models"

# Influx Buckets
BUCKETS = ["1_2_2", "1_2_7", "1_3_10", "1_3_11", "1_3_14", "1_4_12", "1_4_13"]  
BUCKETS_PIR = ["1_2_2", "1_3_11", "1_3_14", "1_4_13"]
BUCKET_CORRIDOR = "1_2_2"
BUCKET_BATHROOM = "1_3_11"
BUCKET_DOOR = "1_3_14"
BUCKET_BED = "1_4_13"

# pir_buckets = {
#         "1_2_2": "corridor",
#         "1_3_11": "bathroom",
#         "1_3_14": "door",
#         "1_4_13": "bed",
#     }

# Influx Buckets
bucket_mapping = {
    "1_2_2": "corridor",
    "1_3_11": "bathroom",
    "1_3_14": "door",
    "1_4_13": "bed",
}


# ------------------------------ INFLUXDB FUNCTIONS ------------------------------

# Fetch data (inspired by the sif-viz-component fetch data structure)
def fetch_data(bucket, measurement, field):

    with InfluxDBClient(
        url=INFLUX_TOKEN, 
        org=INFLUX_ORG, 
        sername=INFLUX_USER, 
        password=INFLUX_PASS, 
        verify_ssl=False) as client:
            p = {
                "_start": timedelta(days=-7),  # "fetch data starting from 7 days ago".
            }

            query_api = client.query_api()
            tables = query_api.query(f'''
                                    from(bucket: "{bucket}") |> range(start: _start)
                                    |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                                    |> filter(fn: (r) => r["_type"] == "{"sensor-value"}")
                                    |> filter(fn: (r) => r["_field"] == "{field}")
                                    ''', params=p)          
            obj = []
            
            base_logger.info(tables)
            for table in tables:
                for record in table.records:
                    val = {}
                    base_logger.info(record)
                    val["bucket"] = bucket
                    val["timestamp"] = record["_time"].timestamp() * 1000
                    val["value"] = record["_value"]
                    if len(val.keys()) != 0:
                        obj.append(val)

            return obj


# ------------------------------ DATA PROCESSING FUNCTIONS ------------------------------

def fetch_data_arrangement():   # Makes easier readable values for the model 

    # Fetch data for each bucket individually
    bathroomfetch = fetch_data(BUCKET_BATHROOM, "PIR", "roomID")
    corridorfetch = fetch_data(BUCKET_CORRIDOR, "PIR", "roomID")
    bedfetch = fetch_data(BUCKET_BED, "PIR", "roomID")
    doorfetch = fetch_data(BUCKET_DOOR, "door", "roomID2")

    # Add bucket identifier to each fetched dataset
    for record in bathroomfetch:
        record["bucket"] = "1_3_11"  # BUCKET_BATHROOM
    for record in corridorfetch:
        record["bucket"] = "1_2_2"   # BUCKET_CORRIDOR
    for record in bedfetch:
        record["bucket"] = "1_4_13"  # BUCKET_BED
    for record in doorfetch:
        record["bucket"] = "1_3_14"  # BUCKET_DOOR

    # Merge all fetched data
    all_fetched = bathroomfetch + corridorfetch + bedfetch + doorfetch

    # Create a pandas DataFrame
    df = pd.DataFrame(all_fetched)

    # Map bucket to value
    df["value"] = df["bucket"].map(bucket_mapping)

    # Convert timestamp and sort
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.sort_values("timestamp")
    
    return df


def data_sorting(df):   

    df_sorted = df.sort_values(by='timestamp')
    df_sorted['human_readable_time'] = pd.to_datetime(df_sorted['timestamp'], unit='ms')
    print(df_sorted.head(40))

    return df_sorted


# ------------------------------ TRAINING OCUPANCY MODEL FUNCTIONS ------------------------------

#WITHOUT SEASONALITY
def calculate_stays(df):
    stays = []
    current_stay = None

    for index, row in df.iterrows():
        if current_stay is None:
            current_stay = {
                'room': row['value'],
                'start': row['timestamp'],
                'end': row['timestamp']
            }
        elif row['value'] == current_stay['room']:
            current_stay['end'] = row['timestamp']
        else:
            current_stay['duration'] = (current_stay['end'] - current_stay['start']).total_seconds()
            stays.append(current_stay)
            current_stay = {
                'room': row['value'],
                'start': row['timestamp'],
                'end': row['timestamp']
            }

    if current_stay is not None:
        current_stay['duration'] = (current_stay['end'] - current_stay['start']).total_seconds()
        stays.append(current_stay)

    stays_df = pd.DataFrame(stays)
    #print(stays_df)

    return stays_df


#WITH SEASONALITY
def calculate_seasonal_stays(df):
    # Extract day of the week and hour from the start time
    df['day_of_week'] = df['start'].dt.dayofweek
    df['hour_of_day'] = df['start'].dt.hour

    # Group by room, day of the week, and hour of the day
    grouped = df.groupby(['room', 'day_of_week', 'hour_of_day'])

    # Calculate the number of visits and average duration
    seasonal_stats = grouped['duration'].agg(['count', 'mean']).reset_index()
    seasonal_stats.rename(columns={'count': 'number_of_visits', 'mean': 'average_duration'}, inplace=True)

    # Sort by day of the week and hour of the day
    seasonal_stats = seasonal_stats.sort_values(by=['day_of_week', 'hour_of_day'])

    return seasonal_stats


# ------------------------------ EMERGENCY FUNCTIONS ------------------------------

def check_emergency(stays_df, seasonal_stays_df):
    for index, row in stays_df.iterrows():
        # Find the corresponding average duration
        avg_duration = seasonal_stays_df[
            (seasonal_stays_df['room'] == row['room']) &
            (seasonal_stays_df['day_of_week'] == row['day_of_week']) &
            (seasonal_stays_df['hour_of_day'] == row['hour_of_day'])
        ]['average_duration'].values
        
        if len(avg_duration) > 0:
            if row['duration'] > avg_duration[0]:
                print(f"Emergency: {row['room']} at {row['start']} with duration {row['duration']} seconds")
            else:
                print(f"Normal: {row['room']} at {row['start']} with duration {row['duration']} seconds")


# ------------------------------ MINIO MODEL FUNCTIONS ------------------------------

def load_latest_model_minio():
    # Minio Initialize Client
    client = Minio(
        endpoint=MINIO_ENDPOINT, 
        access_key=MINIO_ACCESS_KEY, 
        secret_key=MINIO_SECRET_KEY, 
        secure=False
    )
    base_logger.info("Initialized MinIO client successfully.")

    try:
        # Get the latest model version
        version_file_name = "latest_model_version.txt"
        response = client.get_object(MINIO_BUCKET, version_file_name)
        latest_model_name = response.data.decode("utf-8")
        response.close()
        response.release_conn()
        base_logger.info(f"Latest model version: {latest_model_name}")

        # Load the latest model
        response = client.get_object(MINIO_BUCKET, latest_model_name)
        model_data = response.data.decode("utf-8")
        response.close()
        response.release_conn()
        model = pd.read_json(BytesIO(model_data.encode("utf-8")))
        base_logger.info(f"Loaded model from MinIO: {latest_model_name}")

        return model

    except Exception as e:
        base_logger.error(f"Error loading model from Minio: {e}")
        return None


# ------------------------------ MAIN APPLICATION  ------------------------------
# ------------------------------ OCUPANCY EVENTS ------------------------------ 

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

# ------------------------------ MOTION  EVENTS ------------------------------ 

class TrainMotionModelEvent(BaseEventFabric): # Every end of a period
    def __init__(self):
        super(TrainMotionModelEvent, self).__init__()

    def call(self, *args, **kwargs):
        evt_name = "TrainMotionModelEvent"
        data = {"message": "Triggering Motion Model Training"}
        base_logger.info(f"Event generated: {evt_name}")
        return evt_name, data

class AnalyzeMotionEvent(BaseEventFabric): # Every end of a period
    def __init__(self):
        super(AnalyzeMotionEvent, self).__init__()

    def call(self, *args, **kwargs):
        evt_name = "AnalyzeMotionEvent"
        data = {"message": "Triggering Motion Event Analysis"}
        base_logger.info(f"Event generated: {evt_name}")
        return evt_name, data

# ------------------------------ OCCUPANCY EMERGENCY DETECTION ------------------------------ 

# Emergency Detection Function
async def EmergencyDetectionFunction(request: Request):
    
    base_logger.info("EmergencyDetectionFunction called")
    data = await request.json()
    base_logger.info(f"EmergencyDetectionFunction received data: {data}")

    base_logger.info("Loading model from minio")
    model = load_latest_model_minio()

    base_logger.info("Fetching data")
    new_data=fetch_data_arrangement()
    data_sorted=data_sorting(new_data)

    base_logger.info("Calculating average times")
    stays_df = calculate_stays(data_sorted)
    seasonal_stays_df = calculate_seasonal_stays(stays_df)

    base_logger.info("Checking for an emergency")
    emergency_status=check_emergency(stays_df, seasonal_stays_df)
    return {"status": "success"}

# ------------------------------ MOTION DETECTION ------------------------------ 

async def MotionAnalysisFunction(request: Request):

    return



# ------------------------------ EVENT FABRIC ------------------------------ 

train_occupancy_model_event = TrainOccupancyModelEvent()
base_logger.info("train_occupancy_model_event instatiated.")
check_emergency_event = CheckEmergencyEvent()
base_logger.info("check_emergency_event instatiated.")

# ------------------------------ OCUPANCY TRIGGERS ------------------------------ 

periodicTrainModelTrigger = PeriodicTrigger(
    TrainOccupancyModelEvent(), 
    duration="24h", 
    wait_time="30s")

periodicCheckEmergencyTrigger = PeriodicTrigger(
    CheckEmergencyEvent(), 
    duration="30m", 
    wait_time="30s")

base_logger.info("Occupancy Triggers added for TrainOccupancyModelEvent and CheckEmergencyEvent.")

# ------------------------------ MOTION TRIGGERS ------------------------------ 

periodicTrainMotionModelEvent = PeriodicTrigger(
    TrainMotionModelEvent(), 
    duration="24h", 
    wait_time="30s")

periodicAnalyzeMotionEvent = PeriodicTrigger(
    AnalyzeMotionEvent(), 
    duration="24h", 
    wait_time="30s")

base_logger.info("Motion Triggers added for TrainOccupancyModelEvent and CheckEmergencyEvent.")

# ------------------------------ APP GATEWAY ------------------------------ 

app = LocalGateway()
base_logger.info("Getaway initiated.")

# Deploy Functions to LocalGateway

app.deploy(EmergencyDetectionFunction,
           name="EmergencyDetectionFunction",
           evts="CheckEmergencyEvent",
           method="POST")
base_logger.info("EmergencyDetectionFunction deployed.")


app.deploy(MotionAnalysisFunction,
           name="MotionAnalysisFunction",
           evts="AnalyzeMotionEvent",
           method="POST")
base_logger.info("MotionAnalysisFunction deployed.")

























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










# def check_emergency(data, model):
#     base_logger.info("Checking for emergency")

#     # Read and parse the JSON from the BytesIO object
#     model_json = model.decode(encoding="utf-8")
#     model_data = json.loads(model_json)

#     # Validate the structure of the model data
#     if not all(key in model_data for key in ["bucket", "time_interval", "average_duration_minutes"]):
#         base_logger("Model JSON does not have the required keys.")

#     bucket_mapping = {
#         "1_2_2": "corridor",
#         "1_3_11": "bathroom",
#         "1_3_14": "door",
#         "1_4_13": "bed",
#     }

#     base_logger.info("data of past 6 hours:" + str(data))
#     base_logger.info("latest model data: " + str(model_data))

#     if len(data) == 0:
#         return True, "Sensors failed; there might be an undetected emergency", "general", 0

#     data["room"] = data["bucket"].replace(bucket_mapping)
#     data = data.sort_values(by="timestamp").reset_index(drop=True)
#     data["stay_id"] = (data["room"] != data["room"].shift()).cumsum()
#     # Get the last stay (all others are irrelevant as the pearson clearly moved)
#     last_stay = data[data["stay_id"] == data["stay_id"].iloc[-1]]
#     room = last_stay["room"].iloc[0]
#     if room == "door":
#         return False, "No emergency detected. Patient is not at home.", "general", 0
#     start_time = last_stay["timestamp"].iloc[0]
#     end_time = last_stay["timestamp"].iloc[-1]
#     current_duration = (end_time - start_time).total_seconds() / 60

#     hour = end_time.hour
#     if 0 <= hour < 6:
#         time_interval = "00-06"
#     elif 6 <= hour < 12:
#         time_interval = "06-12"
#     elif 12 <= hour < 17:
#         time_interval = "12-17"
#     else:
#         time_interval = "17-00"
    
#     # Find the average duration for the room and timespan from the model
#     avg_duration = None
#     for i in range(len(model_data["bucket"])):
#         if model_data["bucket"][str(i)] == room and model_data["time_interval"][str(i)] == time_interval:
#             avg_duration = model_data["average_duration_minutes"][str(i)]
#             break
    
#     if avg_duration is None:
#         return True, f"No model data available for the current room {room} and time interval {time_interval}" , room, 0
    
#     # Check if the current duration is 20% longer than the average
#     threshold_level_2 = avg_duration * 1.2
#     threshold_level_1 = avg_duration * 1.1
#     is_longer = current_duration > threshold_level_2
#     is_longer_level_1 = current_duration > threshold_level_1

#     if is_longer:
#         return True, f"Emergency detected in {room}. Patient has been in the room for {current_duration} minutes, which is at least 20% longer than the average of {avg_duration} minutes", room, 2
#     elif is_longer_level_1:
#         return True, f"Emergency detected in {room}. Patient has been in the room for {current_duration} minutes, which is at least 10% longer than the average of {avg_duration} minutes", room, 1
   
#     return False, f"No emergency detected in {room}. Patient has been in the room for {current_duration} minutes, which is within the normal range of {avg_duration} minutes", room, 0











































































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
