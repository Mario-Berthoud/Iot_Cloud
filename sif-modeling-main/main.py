########################
#       MODELING       #
########################

from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, ExampleEventFabric

from influxdb_client import InfluxDBClient
from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from minio import Minio
from io import BytesIO
import pandas as pd


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
        username=INFLUX_USER, 
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

# Base version 
def train_model(df_sorted):

    # Calculate the time differences between consecutive rows
    df_sorted['time_diff'] = df_sorted['timestamp'].diff()

    # Filter out rows where the value changes
    df_filtered = df_sorted[df_sorted['value'] != df_sorted['value'].shift()]

    # Group by the value column and calculate the mean and standard deviation of the time differences
    time_stats = df_filtered.groupby('value')['time_diff'].agg(['mean', 'std'])

    return time_stats

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


def identify_outliers(df, seasonal_stats):
    # Merge the original dataframe with the seasonal statistics
    merged_df = df.merge(seasonal_stats, on=['room', 'day_of_week', 'hour_of_day'], how='left')

    # Identify outliers where the duration is longer than the average duration
    merged_df['is_outlier'] = merged_df['duration'] > merged_df['average_duration']

    # Filter out the outliers
    outliers_df = merged_df[merged_df['is_outlier']]

    return outliers_df


# ------------------------------ MINIO MODEL FUNCTIONS ------------------------------

def save_model_minio(model):
    # Minio Initialize Client
    client = Minio(
        endpoint=MINIO_ENDPOINT, 
        access_key=MINIO_ACCESS_KEY, 
        secret_key=MINIO_SECRET_KEY, 
        secure=False
    )
    base_logger.info("Initialized MinIO client successfully.")

    found = client.bucket_exists(MINIO_BUCKET)
    if not found:
        client.make_bucket(MINIO_BUCKET)
        base_logger.info(f"Bucket '{MINIO_BUCKET}' created.")
    else:
        base_logger.info(f"Bucket '{MINIO_BUCKET}' already exists.")

    # Timestamp object 
    current_time = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    data = pd.DataFrame.to_json(model).encode("utf-8")
    object_name = f"model_{current_time}.json"

    # Save model to Minio
    try:
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type="application/json",
            metadata={'time': current_time}
        )
        base_logger.info(f"Model saved to MinIO as '{object_name}' in bucket '{MINIO_BUCKET}'.")

        # Save the version of the model to a text file
        version_file_name = "latest_model_version.txt"
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=version_file_name,
            data=BytesIO(object_name.encode("utf-8")),
            length=len(object_name),
            content_type="text/plain"
        )
        base_logger.info(f"Model version saved to MinIO as '{version_file_name}' in bucket '{MINIO_BUCKET}'.")

    except Exception as e:
        base_logger.error(f"Error storing model to Minio: {e}")
    base_logger.info(f"Stored model_{current_time}.json to Minio")

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

app = LocalGateway()
base_logger.info("Getaway initiated.")

# ------------------------------ OCCUPANCY MODEL FUNCTION  ------------------------------

async def CreateOccupancyModelFunction(request: Request):
    base_logger.info("Function ocupancy_model_creation called.")

    base_logger.info("Function create occupancy model called.")
    data_recieved = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {data_recieved}")

    base_logger.info("Fetching data")
    new_data=fetch_data_arrangement()
    data_sorted=data_sorting(new_data)

    base_logger.info("Calculating average times")
    stays_df = calculate_stays(data_sorted)  
    seasonal_stays_df = calculate_seasonal_stays(stays_df)

    base_logger.info("Calculating outliers")
    outliers_df = identify_outliers(stays_df, seasonal_stays_df)

    base_logger.info("Saving ocupancy model to minio")
    save_model_minio(time_stats)  # cambia time_stats por tu output del modelo final 
    load_latest_model_minio()   
    base_logger.info("model trained and stored")

    return {"status": 200, "message": "Model trained and stored"}

app.deploy(CreateOccupancyModelFunction,
    name="CreateOccupancyModelFunction",
    evts="TrainOccupancyModelEvent",
    method="POST",
)
base_logger.info("CreateOccupancyModelFunction deployed.")

# ------------------------------ MOTION MODEL FUNCTION  ------------------------------

async def CreateMotionModelFunction(request: Request):
    base_logger.info("Function CreateMotionModelFunction called.")

    base_logger.info("Function create occupancy model called.")
    data_recieved = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {data_recieved}")

    base_logger.info("Fetching data")
    new_data=fetch_data_arrangement()
    data_sorted=data_sorting(new_data)



    return {"status": 200, "message": "Model trained and stored"}

app.deploy(CreateMotionModelFunction,
    name="CreateMotionModelFunction",
    evts="TrainMotionModelEvent",
    method="POST",
)
base_logger.info("CreateMotionModelFunction deployed.")