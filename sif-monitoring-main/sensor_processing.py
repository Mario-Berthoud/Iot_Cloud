import pandas as pd
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta

# Constants for InfluxDB
INFLUX_ORG = "wise2024"
INFLUX_URL = "http://192.168.1.132:8086"
INFLUX_USER = "admin"
INFLUX_PASS = "secure_influx_iot_user"
INFLUX_TOKEN = "aXO7n14FVAl0YzVJEq4FaQCZnlkeeegIKHk-0GioBJqTWTGZSFI0LqfPXSIP32S2xdFROelXbP51YtfJmh9lCg==" 

# Bucket Configuration
PIR_BUCKETS = ["1_2_2", "1_3_11", "1_4_13"]
DOOR_BUCKETS = ["1_3_14"]
BATTERY_BUCKETS = ["1_2_7", "1_3_10", "1_4_12"]

# Fetch data from a single bucket
def fetch_data(bucket, measurement, field, hours=1):
    try:
        with InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
            username=INFLUX_USER,
            password=INFLUX_PASS,
            verify_ssl=False
        ) as client:
            
            p = {
                "_start": timedelta(hours=-hours),
            }

            query_api = client.query_api()
            tables = query_api.query(f'''
                                    from(bucket: "{bucket}") |> range(start: _start)
                                    |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                                    |> filter(fn: (r) => r["_type"] == "{"sensor-value"}")
                                    |> filter(fn: (r) => r["_field"] == "{field}")
                                    ''', params=p)

            data = []
            for table in tables:
                for record in table.records:
                    data.append({
                        "bucket": bucket,
                        "time": record["_time"],
                        "value": record["_value"]
                    })
            return pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


# Fetch all relevant sensor data
def fetch_all_data(hours=1):
    pir_data = pd.concat([fetch_data(bucket, "PIR", "roomID", hours) for bucket in PIR_BUCKETS])
    door_data = pd.concat([fetch_data(bucket, "door", "roomID2", hours) for bucket in DOOR_BUCKETS])
    battery_data = pd.concat([fetch_data(bucket, "battery", ["soc", "voltage"], hours) for bucket in BATTERY_BUCKETS])

    return pir_data, door_data, battery_data


# Process sensor data to calculate visit durations
def process_sensor_data(hours=1):
    pir_data, door_data, _ = fetch_all_data(hours)

    # Combine PIR and door sensor data
    combined_data = pd.concat([pir_data, door_data]).sort_values("time")
    combined_data["room_change"] = (combined_data["value"] != combined_data["value"].shift()).astype(int)
    combined_data["group_id"] = combined_data["room_change"].cumsum()

    # Calculate visit durations
    visit_durations = combined_data.groupby("group_id").agg(
        room=("value", "first"),
        start_time=("time", "min"),
        end_time=("time", "max")
    )
    visit_durations["duration"] = (visit_durations["end_time"] - visit_durations["start_time"]).dt.total_seconds()

    return visit_durations
