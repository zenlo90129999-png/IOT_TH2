import os
from pathlib import Path

from dotenv import load_dotenv


# =========================================
# ĐƯỜNG DẪN PROJECT
# =========================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ENV_FILE = ROOT_DIR / ".env"

load_dotenv(
    ENV_FILE,
    override=True
)


# =========================================
# MQTT
# =========================================

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "broker.emqx.io"
)

MQTT_PORT = int(
    os.getenv(
        "MQTT_PORT",
        "1883"
    )
)

MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "ptit/iot/B23DCAT224/esp32/sensor"
)

DEVICE_ID = os.getenv(
    "DEVICE_ID",
    "ESP32-B23DCAT224"
)


# =========================================
# INFLUXDB
# =========================================

INFLUX_URL = os.getenv(
    "INFLUX_URL",
    "http://localhost:8086"
)

INFLUX_TOKEN = os.getenv(
    "INFLUX_TOKEN",
    ""
)

INFLUX_ORG = os.getenv(
    "INFLUX_ORG",
    "PTIT"
)

INFLUX_BUCKET = os.getenv(
    "INFLUX_BUCKET",
    "iot_data"
)


# =========================================
# KIỂM TRA CONFIG
# =========================================

def check_config():

    token = (
        INFLUX_TOKEN or ""
    ).strip()

    if not token:
        raise RuntimeError(
            "Chua cau hinh INFLUX_TOKEN "
            "trong file .env"
        )

    if token == "THAY_TOKEN_INFLUXDB_CUA_BAN":
        raise RuntimeError(
            "INFLUX_TOKEN van dang la "
            "gia tri mau trong .env"
        )

    return True