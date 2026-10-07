import json
import time

import paho.mqtt.client as mqtt

from influxdb_client import (
    InfluxDBClient,
    Point,
    WritePrecision
)

from influxdb_client.client.write_api import (
    SYNCHRONOUS
)

from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC,
    INFLUX_URL,
    INFLUX_TOKEN,
    INFLUX_ORG,
    INFLUX_BUCKET,
    check_config
)


# =====================================================
# KIỂM TRA CONFIG
# =====================================================

check_config()


# =====================================================
# INFLUXDB
# =====================================================

influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = influx_client.write_api(
    write_options=SYNCHRONOUS
)


# =====================================================
# THEO DÕI SEQUENCE
# =====================================================

last_sequence = {}
last_uptime = {}


# =====================================================
# VALIDATE DATA
# =====================================================

def validate_data(data):

    required_fields = [
        "device_id",
        "temperature",
        "humidity",
        "distance_cm",
        "rssi",
        "sequence",
        "uptime_s",
        "ts_ms"
    ]

    # Kiểm tra đủ trường

    for field in required_fields:

        if field not in data:

            print(
                f"[INVALID] Missing field: {field}"
            )

            return False

    # Kiểm tra kiểu dữ liệu

    try:

        temperature = float(
            data["temperature"]
        )

        humidity = float(
            data["humidity"]
        )

        distance = float(
            data["distance_cm"]
        )

        int(data["rssi"])
        int(data["sequence"])
        int(data["uptime_s"])
        int(data["ts_ms"])

    except (
        ValueError,
        TypeError
    ):

        print(
            "[INVALID] Invalid data type"
        )

        return False

    # ----------------------------------------------
    # Kiểm tra miền hợp lệ
    # ----------------------------------------------

    if not (
        -40 <= temperature <= 80
    ):

        print(
            "[INVALID] Temperature out of range"
        )

        return False

    if not (
        0 <= humidity <= 100
    ):

        print(
            "[INVALID] Humidity out of range"
        )

        return False

    if not (
        2 <= distance <= 400
    ):

        print(
            "[INVALID] Distance out of range"
        )

        return False

    return True


# =====================================================
# KIỂM TRA DUPLICATE / PACKET LOSS
# =====================================================

def check_sequence(data):

    device_id = data["device_id"]

    sequence = int(
        data["sequence"]
    )

    uptime = int(
        data["uptime_s"]
    )

    previous_sequence = (
        last_sequence.get(
            device_id
        )
    )

    previous_uptime = (
        last_uptime.get(
            device_id
        )
    )

    # ----------------------------------------------
    # Lần đầu nhận device
    # ----------------------------------------------

    if previous_sequence is None:

        last_sequence[
            device_id
        ] = sequence

        last_uptime[
            device_id
        ] = uptime

        return True

    # ----------------------------------------------
    # ESP32 restart
    # ----------------------------------------------

    if (
        previous_uptime is not None
        and
        uptime < previous_uptime
    ):

        print(
            "[INFO] Device restart detected"
        )

        last_sequence[
            device_id
        ] = sequence

        last_uptime[
            device_id
        ] = uptime

        return True

    # ----------------------------------------------
    # Duplicate
    # ----------------------------------------------

    if (
        sequence
        == previous_sequence
    ):

        print(
            "[DUPLICATE] "
            f"sequence={sequence}"
        )

        return False

    # ----------------------------------------------
    # Packet loss
    # ----------------------------------------------

    if (
        sequence
        > previous_sequence + 1
    ):

        missing = (
            sequence
            - previous_sequence
            - 1
        )

        print(
            "[WARNING] Possible packet loss"
        )

        print(
            f"Missing packets: {missing}"
        )

        print(
            f"Previous sequence: {previous_sequence}"
        )

        print(
            f"Current sequence : {sequence}"
        )

    last_sequence[
        device_id
    ] = sequence

    last_uptime[
        device_id
    ] = uptime

    return True


# =====================================================
# MQTT CALLBACK: CONNECT
# =====================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    print()
    print(
        "===================================="
    )

    print(
        "MQTT CONNECTED"
    )

    print(
        f"Broker : {MQTT_BROKER}"
    )

    print(
        f"Port   : {MQTT_PORT}"
    )

    print(
        f"Topic  : {MQTT_TOPIC}"
    )

    print(
        f"Code   : {reason_code}"
    )

    print(
        "===================================="
    )

    client.subscribe(
        MQTT_TOPIC
    )


# =====================================================
# MQTT CALLBACK: DISCONNECT
# =====================================================

def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):

    print(
        "[MQTT] Disconnected"
    )

    print(
        f"Reason: {reason_code}"
    )


# =====================================================
# MQTT CALLBACK: MESSAGE
# =====================================================

def on_message(
    client,
    userdata,
    msg
):

    receive_timestamp_ms = int(
        time.time() * 1000
    )

    print()
    print(
        "===================================="
    )

    print(
        "[MQTT] Message received"
    )

    print(
        f"Topic: {msg.topic}"
    )

    try:

        # ------------------------------------------
        # JSON decode
        # ------------------------------------------

        raw_payload = (
            msg.payload.decode(
                "utf-8"
            )
        )

        print(
            "Payload:"
        )

        print(
            raw_payload
        )

        data = json.loads(
            raw_payload
        )

        # ------------------------------------------
        # Validate
        # ------------------------------------------

        if not validate_data(
            data
        ):

            print(
                "[SKIP] Invalid data"
            )

            return

        # ------------------------------------------
        # Duplicate / packet loss
        # ------------------------------------------

        if not check_sequence(
            data
        ):

            print(
                "[SKIP] Duplicate packet"
            )

            return

        # ------------------------------------------
        # LẤY DỮ LIỆU
        # ------------------------------------------

        device_id = str(
            data["device_id"]
        )

        temperature = float(
            data["temperature"]
        )

        humidity = float(
            data["humidity"]
        )

        distance = float(
            data["distance_cm"]
        )

        rssi = int(
            data["rssi"]
        )

        sequence = int(
            data["sequence"]
        )

        uptime = int(
            data["uptime_s"]
        )

        send_timestamp_ms = int(
            data["ts_ms"]
        )

        # ------------------------------------------
        # LATENCY
        # ------------------------------------------

        latency_ms = (
            receive_timestamp_ms
            -
            send_timestamp_ms
        )

        # Nếu NTP ESP32 chưa đồng bộ
        # thì không dùng latency sai

        timestamp_valid = (
            send_timestamp_ms
            > 1_700_000_000_000
        )

        if (
            not timestamp_valid
            or
            latency_ms < 0
            or
            latency_ms > 60000
        ):

            print(
                "[WARNING] "
                "Invalid timestamp / latency"
            )

            latency_ms = -1

        # ------------------------------------------
        # DATABASE WRITE TIME
        # ------------------------------------------

        db_start = (
            time.perf_counter()
        )

        # ------------------------------------------
        # TẠO POINT INFLUXDB
        # ------------------------------------------

        point = (
            Point(
                "sensor_raw"
            )

            .tag(
                "device_id",
                device_id
            )

            .field(
                "temperature",
                temperature
            )

            .field(
                "humidity",
                humidity
            )

            .field(
                "distance_cm",
                distance
            )

            .field(
                "rssi",
                rssi
            )

            .field(
                "sequence",
                sequence
            )

            .field(
                "uptime_s",
                uptime
            )

            .field(
                "receive_ts_ms",
                receive_timestamp_ms
            )

            .field(
                "latency_ms",
                float(
                    latency_ms
                )
            )
        )

        # ------------------------------------------
        # Dùng timestamp ESP32 nếu hợp lệ
        # ------------------------------------------

        if timestamp_valid:

            point = point.time(
                send_timestamp_ms,
                WritePrecision.MS
            )

        # ------------------------------------------
        # WRITE INFLUX
        # ------------------------------------------

        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point
        )

        db_end = (
            time.perf_counter()
        )

        database_write_ms = (
            db_end
            - db_start
        ) * 1000

        # ------------------------------------------
        # OUTPUT
        # ------------------------------------------

        print()
        print(
            "VALID SENSOR DATA"
        )

        print(
            f"Device      : {device_id}"
        )

        print(
            f"Temperature : {temperature:.2f} C"
        )

        print(
            f"Humidity    : {humidity:.2f} %"
        )

        print(
            f"Distance    : {distance:.2f} cm"
        )

        print(
            f"RSSI        : {rssi} dBm"
        )

        print(
            f"Sequence    : {sequence}"
        )

        print(
            f"Uptime      : {uptime} s"
        )

        if latency_ms >= 0:

            print(
                f"E2E latency : {latency_ms:.2f} ms"
            )

        else:

            print(
                "E2E latency : N/A"
            )

        print(
            "DB write    : "
            f"{database_write_ms:.2f} ms"
        )

        print(
            "[SUCCESS] Saved to InfluxDB"
        )

    except json.JSONDecodeError:

        print(
            "[ERROR] Invalid JSON"
        )

    except Exception as error:

        print(
            "[ERROR]",
            error
        )

    print(
        "===================================="
    )


# =====================================================
# MAIN
# =====================================================

def main():

    client = mqtt.Client(
        callback_api_version=
            mqtt.CallbackAPIVersion.VERSION2,

        client_id=
            "PTIT-B23DCAT224-GATEWAY"
    )

    client.on_connect = (
        on_connect
    )

    client.on_disconnect = (
        on_disconnect
    )

    client.on_message = (
        on_message
    )

    client.reconnect_delay_set(
        min_delay=1,
        max_delay=10
    )

    print(
        "===================================="
    )

    print(
        "BAI THUC HANH SO 2"
    )

    print(
        "MQTT -> INFLUXDB COLLECTOR"
    )

    print(
        "===================================="
    )

    print(
        f"Connecting to {MQTT_BROKER}..."
    )

    client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        60
    )

    try:

        client.loop_forever()

    except KeyboardInterrupt:

        print()
        print(
            "Stopping collector..."
        )

    finally:

        client.disconnect()

        influx_client.close()


if __name__ == "__main__":

    main()