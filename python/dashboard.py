import pandas as pd
import streamlit as st

from influxdb_client import InfluxDBClient
from streamlit_autorefresh import st_autorefresh

from config import (
    DEVICE_ID,
    INFLUX_URL,
    INFLUX_TOKEN,
    INFLUX_ORG,
    INFLUX_BUCKET,
    check_config
)


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="IoT Monitoring Dashboard",
    page_icon="📡",
    layout="wide"
)


# =====================================================
# AUTO REFRESH 5 GIÂY
# =====================================================

st_autorefresh(
    interval=5000,
    key="iot_refresh"
)


# =====================================================
# TITLE
# =====================================================

st.title("📡 IoT Sensor Monitoring Dashboard")

st.caption(
    "Bài thực hành số 2 - "
    "Thu thập, lưu trữ và tiền xử lý dữ liệu IoT"
)

st.markdown(
    f"**Device:** `{DEVICE_ID}`"
)

st.divider()


# =====================================================
# CONFIG CHECK
# =====================================================

try:
    check_config()

except Exception as error:

    st.error(
        f"Lỗi cấu hình: {error}"
    )

    st.stop()


# =====================================================
# INFLUXDB CONNECTION
# =====================================================

try:

    client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )

    query_api = client.query_api()

except Exception as error:

    st.error(
        f"Không thể kết nối InfluxDB: {error}"
    )

    st.stop()


# =====================================================
# LOAD MEASUREMENT
# =====================================================

def load_measurement(
    measurement,
    start="-1h"
):

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start})

      |> filter(
          fn: (r) =>
          r["_measurement"] == "{measurement}"
      )

      |> filter(
          fn: (r) =>
          r["device_id"] == "{DEVICE_ID}"
      )
    '''

    try:

        result = (
            query_api
            .query_data_frame(
                query
            )
        )

    except Exception as error:

        st.error(
            f"Lỗi query {measurement}: {error}"
        )

        return pd.DataFrame()

    # Có thể trả về list DataFrame
    if isinstance(
        result,
        list
    ):

        frames = [
            df
            for df in result
            if not df.empty
        ]

        if not frames:
            return pd.DataFrame()

        result = pd.concat(
            frames,
            ignore_index=True
        )

    if result.empty:
        return pd.DataFrame()

    # Chuyển _field thành column
    try:

        df = result.pivot_table(
            index="_time",
            columns="_field",
            values="_value",
            aggfunc="last"
        )

    except Exception as error:

        st.error(
            f"Lỗi pivot dữ liệu: {error}"
        )

        return pd.DataFrame()

    df.index = pd.to_datetime(
        df.index
    )

    df = df.sort_index()

    return df


# =====================================================
# LOAD RAW DATA
# =====================================================

raw_df = load_measurement(
    "sensor_raw",
    "-1h"
)


# =====================================================
# KIỂM TRA RAW DATA
# =====================================================

if raw_df.empty:

    st.warning(
        "Chưa tìm thấy dữ liệu sensor_raw."
    )

    st.info(
        "Hãy kiểm tra InfluxDB và chạy "
        "mqtt_to_influx.py trước."
    )

    st.stop()


# =====================================================
# LATEST VALUES
# =====================================================

latest = raw_df.iloc[-1]


st.subheader(
    "🔴 Dữ liệu cảm biến hiện tại"
)


col1, col2, col3 = (
    st.columns(3)
)


# Temperature

temperature = latest.get(
    "temperature",
    float("nan")
)

col1.metric(
    "🌡️ Nhiệt độ",
    f"{temperature:.2f} °C"
)


# Humidity

humidity = latest.get(
    "humidity",
    float("nan")
)

col2.metric(
    "💧 Độ ẩm",
    f"{humidity:.2f} %"
)


# Distance

distance = latest.get(
    "distance_cm",
    float("nan")
)

col3.metric(
    "📏 Khoảng cách",
    f"{distance:.2f} cm"
)


# =====================================================
# DEVICE STATUS
# =====================================================

st.subheader(
    "📶 Trạng thái thiết bị"
)


c1, c2, c3, c4 = (
    st.columns(4)
)


rssi = latest.get(
    "rssi",
    float("nan")
)

sequence = latest.get(
    "sequence",
    float("nan")
)

uptime = latest.get(
    "uptime_s",
    float("nan")
)

latency = latest.get(
    "latency_ms",
    float("nan")
)


c1.metric(
    "WiFi RSSI",
    f"{rssi:.0f} dBm"
)


c2.metric(
    "Sequence",
    f"{sequence:.0f}"
)


c3.metric(
    "Uptime",
    f"{uptime:.0f} s"
)


if (
    pd.notna(latency)
    and latency >= 0
):

    c4.metric(
        "E2E Latency",
        f"{latency:.0f} ms"
    )

else:

    c4.metric(
        "E2E Latency",
        "N/A"
    )


st.divider()


# =====================================================
# TEMPERATURE + HUMIDITY
# =====================================================

st.subheader(
    "🌡️ Nhiệt độ và độ ẩm"
)


temp_humi_columns = [
    col
    for col in [
        "temperature",
        "humidity"
    ]
    if col in raw_df.columns
]


if temp_humi_columns:

    st.line_chart(
        raw_df[
            temp_humi_columns
        ],
        height=350
    )


# =====================================================
# DISTANCE
# TÁCH RIÊNG VÌ THANG 0-400 CM
# =====================================================

st.subheader(
    "📏 Khoảng cách HC-SR04"
)


if (
    "distance_cm"
    in raw_df.columns
):

    st.line_chart(
        raw_df[
            ["distance_cm"]
        ],
        height=350
    )


# =====================================================
# NETWORK
# =====================================================

st.subheader(
    "📡 WiFi RSSI"
)


if "rssi" in raw_df.columns:

    st.line_chart(
        raw_df[
            ["rssi"]
        ],
        height=250
    )


# =====================================================
# LATENCY
# =====================================================

st.subheader(
    "⏱️ Độ trễ"
)


if (
    "latency_ms"
    in raw_df.columns
):

    latency_df = raw_df[
        raw_df[
            "latency_ms"
        ] >= 0
    ][
        ["latency_ms"]
    ]

    if not latency_df.empty:

        st.line_chart(
            latency_df,
            height=250
        )

        avg_latency = (
            latency_df[
                "latency_ms"
            ].mean()
        )

        min_latency = (
            latency_df[
                "latency_ms"
            ].min()
        )

        max_latency = (
            latency_df[
                "latency_ms"
            ].max()
        )


        l1, l2, l3 = (
            st.columns(3)
        )


        l1.metric(
            "Trung bình",
            f"{avg_latency:.2f} ms"
        )

        l2.metric(
            "Nhỏ nhất",
            f"{min_latency:.2f} ms"
        )

        l3.metric(
            "Lớn nhất",
            f"{max_latency:.2f} ms"
        )

    else:

        st.info(
            "Chưa có latency hợp lệ."
        )


st.divider()


# =====================================================
# PROCESSED DATA
# =====================================================

st.subheader(
    "🧹 Dữ liệu sau tiền xử lý"
)


processed_df = load_measurement(
    "sensor_processed",
    "-24h"
)


if processed_df.empty:

    st.warning(
        "Chưa có sensor_processed."
    )

    st.info(
        "Hãy chạy: python python\\preprocess.py"
    )

else:

    # ================================================
    # TEMPERATURE PROCESSED
    # ================================================

    temperature_columns = [
        col
        for col in [
            "temperature",
            "temperature_rolling_mean"
        ]
        if col in processed_df.columns
    ]

    if temperature_columns:

        st.markdown(
            "### 🌡️ Temperature Raw vs Rolling Mean"
        )

        st.line_chart(
            processed_df[
                temperature_columns
            ],
            height=300
        )


    # ================================================
    # HUMIDITY PROCESSED
    # ================================================

    humidity_columns = [
        col
        for col in [
            "humidity",
            "humidity_rolling_mean"
        ]
        if col in processed_df.columns
    ]

    if humidity_columns:

        st.markdown(
            "### 💧 Humidity Raw vs Rolling Mean"
        )

        st.line_chart(
            processed_df[
                humidity_columns
            ],
            height=300
        )


    # ================================================
    # DISTANCE PROCESSED
    # ================================================

    distance_columns = [
        col
        for col in [
            "distance_cm",
            "distance_rolling_mean"
        ]
        if col in processed_df.columns
    ]

    if distance_columns:

        st.markdown(
            "### 📏 Distance Raw vs Rolling Mean"
        )

        st.line_chart(
            processed_df[
                distance_columns
            ],
            height=300
        )


    # ================================================
    # NORMALIZED
    # ================================================

    norm_columns = [
        col
        for col in [
            "temperature_norm",
            "humidity_norm",
            "distance_norm"
        ]
        if col in processed_df.columns
    ]

    if norm_columns:

        st.markdown(
            "### 📊 Dữ liệu chuẩn hóa Min-Max"
        )

        st.line_chart(
            processed_df[
                norm_columns
            ],
            height=300
        )


    # ================================================
    # DELTA
    # ================================================

    delta_columns = [
        col
        for col in [
            "temperature_delta",
            "humidity_delta",
            "distance_delta"
        ]
        if col in processed_df.columns
    ]

    if delta_columns:

        st.markdown(
            "### Δ Delta"
        )

        st.line_chart(
            processed_df[
                delta_columns
            ],
            height=300
        )


st.divider()


# =====================================================
# LATEST RECORDS
# =====================================================

st.subheader(
    "📋 20 bản ghi mới nhất"
)


display_columns = [
    col
    for col in [
        "temperature",
        "humidity",
        "distance_cm",
        "rssi",
        "sequence",
        "uptime_s",
        "latency_ms"
    ]
    if col in raw_df.columns
]


table_df = (
    raw_df[
        display_columns
    ]
    .tail(20)
    .sort_index(
        ascending=False
    )
)


st.dataframe(
    table_df,
    use_container_width=True
)


# =====================================================
# INFO
# =====================================================

st.divider()

st.caption(
    "Dashboard tự động làm mới mỗi 5 giây | "
    "InfluxDB + Streamlit"
)