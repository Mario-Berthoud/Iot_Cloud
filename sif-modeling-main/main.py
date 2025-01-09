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

# -------------------------- CONFIGURATION --------------------------

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

pir_buckets = {
        "1_2_2": "corridor",
        "1_3_11": "bathroom",
        "1_3_14": "door",
        "1_4_13": "bed",
    }

# ------------------------ INFLUXDB FUNCTIONS ------------------------

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


def pandas_data():
    influx_data = []
    for bucket in BUCKETS_PIR:
        if bucket == BUCKET_DOOR:
            data = fetch_data(bucket, "door")
        else:
            data = fetch_data(bucket, "PIR")
        influx_data.extend(data)

    df = pd.DataFrame(influx_data)
    base_logger.info(f"Original data shape: {df.shape}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df = df.sort_values('timestamp')

    return df

def train_model(sensor_data):

    sensor_data["bucket"] = sensor_data["bucket"].replace(pir_buckets)





    return








def save_model_minio(model):
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
    current_time = datetime.datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    data = pd.DataFrame.to_json(model).encode("utf-8")
    object_name = f"model_{current_time}.json"


    # save model to minio
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

    except Exception as e:
        base_logger.error(f"Error storing model to minio: {e}")
    base_logger.info(f"Stored model_{current_time}.json to minio")




    return
                    

def save_model_to_minio(room_stats):
    """
    Save the room statistics model to MinIO, keeping previous versions.
    It also updates a 'latest.txt' file with the name of the newly saved model.
    """

    # Serialize the model (room_stats) to JSON
    model_json = room_stats.to_json(orient='records', date_format='iso')

    # Initialize MinIO client
    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not saved.")
        return

    # Ensure the bucket exists
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        base_logger.info(f"Bucket '{MINIO_BUCKET}' created.")
    else:
        base_logger.info(f"Bucket '{MINIO_BUCKET}' already exists.")

    # Create a timestamped object name to keep old versions
    timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    object_name = f"{MINIO_OBJECT_NAME_PREFIX}_{timestamp_str}.json"

    try:
        # Convert JSON string to bytes
        data = model_json.encode('utf-8')
        data_stream = BytesIO(data)
        data_length = len(data)

        # Upload the versioned model
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type='application/json'
        )
        base_logger.info(f"Model saved to MinIO as '{object_name}' in bucket '{MINIO_BUCKET}'.")

        # Update the "latest" pointer
        latest_data = object_name.encode('utf-8')
        latest_stream = BytesIO(latest_data)
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=LATEST_POINTER_FILE,
            data=latest_stream,
            length=len(latest_data),
            content_type='text/plain'
        )
        base_logger.info(f"'{LATEST_POINTER_FILE}' updated to point to '{object_name}'.")

    except S3Error as e:
        base_logger.error(f"Error uploading model to MinIO: {e}")







app = LocalGateway()
base_logger.info("Modeling Getaway initiated.")

async def ocupancy_model_creation(request: Request):
    base_logger.info("Function ocupancy_model_creation called.")
    base_logger.info("fetching data of past 7 days")
    sensor_data=pandas_data()
    base_logger.info("Calculating average times")
    model = find_averages_by_time_interval(data)
    base_logger.info("saving model to minio")
    save_model(model)
    base_logger.info("model trained and stored")

    return {"status": 200, "message": "Model trained and stored"}

app.deploy(ocupancy_model_creation,
    name="ocupancy_model_creation",
    evts="TrainOccupancyModelEvent",
    method="POST",
)
base_logger.info("ocupancy_model_creation deployed.")


















# def initialize_minio_client():

#     client = Minio(
#         endpoint=MINIO_ENDPOINT, 
#         access_key=MINIO_ACCESS_KEY, 
#         secret_key=MINIO_SECRET_KEY, 
#         secure=False
#         )
#     base_logger.info("Initialized MinIO client successfully.")

#     return 