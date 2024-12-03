import os
import sys
import json
import urllib3
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from logging.handlers import RotatingFileHandler
from influxdb_client.client.write_api import SYNCHRONOUS

from models import ToDo, Information, DeleteBody

TODO_BUCKET = "todo_record"
INFO_BUCKET = "info_record"

INFLUX_ORG = "wise2024"
INFLUX_TOKEN = os.environ.get(
    "INFLUXDB_HOST", None)
INFLUX_USER = os.environ.get("INFLUXDB_USER", None)
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", None)

if INFLUX_TOKEN is None or INFLUX_USER is None or INFLUX_PASS is None:
    raise ValueError("Missing env variables")


BUCKETS = [TODO_BUCKET, INFO_BUCKET]

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("log.log", maxBytes=1e9, backupCount=2),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("viz_component")

with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
    bucket_api = client.buckets_api()
    for bucket in BUCKETS:
        res = bucket_api.find_bucket_by_name(bucket)
        if res:
            logger.info(f"Bucket {bucket} found...")
        else:
            bucket_api.create_bucket(bucket_name=bucket, org=INFLUX_ORG)
            logger.info(f"Bucket {bucket} has been created...")

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=[
                   "*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def fetch_data(bucket, tag, measurement="functions_usage_table",):
    with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
        p = {
            "_start": timedelta(days=-7),
        }

        query_api = client.query_api()
        tables = query_api.query(f'''
                                 from(bucket: "{bucket}") |> range(start: _start)
                                 |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                                 |> filter(fn: (r) => r["_type"] == "{tag}")
                                 ''', params=p)
        obj = []
        logger.info(tables)
        for table in tables:
            for record in table.records:
                val = {}
                logger.info(record)
                val["timestamp"] = record["_time"].timestamp() * 1000
                val["level"] = int(record["_level"])
                if bucket == TODO_BUCKET:
                    val["titel"] = record["_titel"]
                    val["msg"] = record["_value"]
                else:
                    val["summary"] = record["_summary"]
                    val["detail"] = record["_value"]
                if len(val.keys()) != 0:
                    obj.append(val)

        return obj


def store_data(bucket: str, data: Point):
    with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)

        write_api.write(bucket=bucket, record=data)

        logger.info("Point has been successfully recorded")


def delete_data(bucket, measurement, tag, timestamp):
    with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
        delete_api = client.delete_api()
        ts = datetime.fromtimestamp(timestamp/1000.0)
        delete_api.delete(ts, ts,
                          f'_measurement="{measurement}" AND _type="{tag}"',
                          bucket=bucket, org=INFLUX_ORG)


@app.get("/api/todo")
def get_todos():
    return fetch_data(TODO_BUCKET, "todo", "todo_entry")


@app.get("/api/info")
def get_info():
    return fetch_data(INFO_BUCKET, "info", "info_entry")


@app.get("/api/sif")
def get_sif_status():
    http = urllib3.PoolManager()
    res = http.request("GET", "sif-edge.sif:9000/api/status")
    data = json.loads(res.data)
    logger.info(data)
    return data


@app.post("/api/todo")
def save_todo(todo: ToDo):
    point = Point("todo_entry")\
        .tag("_type", "todo")\
        .tag("_titel", todo.titel)\
        .tag("_level", todo.level)\
        .field("msg", todo.msg)\
        .time(todo.timestamp, write_precision=WritePrecision.MS)
    store_data("todo_record", point)


@app.post("/api/info")
def save_info(info: Information):
    point = Point("info_entry")\
        .tag("_type", "info")\
        .tag("_summary", info.summary)\
        .tag("_level", info.level)\
        .field("detail", info.detail)\
        .time(info.timestamp, write_precision=WritePrecision.MS)

    store_data("info_record", point)


@app.delete("/api/todo")
def delete_todo(body: DeleteBody):
    delete_data("todo_record", "todo_entry", "todo", body.timestamp)


@app.delete("/api/info")
def delete_todo(body: DeleteBody):
    delete_data("info_record", "info_entry", "info", body.timestamp)
