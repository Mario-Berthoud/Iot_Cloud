from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, ExampleEventFabric

from influxdb_client import InfluxDBClient
from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from minio import Minio

# InfluxDB credentials and database details
INFLUX_TOKEN = "http://192.168.1.132:8086"
INFLUX_ORG = "wise2024"
INFLUX_USER = "admin"
INFLUX_PASS = "secure_influx_iot_user"

VIZ_COMPONENT_URL = "http://192.168.1.132:9000"

# Influx Buckets
BUCKETS = ["1_2_2", "1_2_7", "1_3_10", "1_3_11", "1_3_14", "1_4_12", "1_4_13"]  

BUCKET_CORRIDOR = "1_2_2"
BUCKET_BATHROOM = "1_3_11"
BUCKET_DOOR = "1_3_14"
BUCKET_BED = "1_4_13"

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

                    # if bucket == BUCKETS:
                    #     val["titel"] = record["_titel"]
                    #     val["msg"] = record["_value"]
                    # else:
                    #     val["summary"] = record["_summary"]
                    #     val["detail"] = record["_value"]
                    if len(val.keys()) != 0:
                        obj.append(val)

            return obj
    

