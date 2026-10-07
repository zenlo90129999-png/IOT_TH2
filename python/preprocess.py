from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.preprocessing import MinMaxScaler

from influxdb_client import (
    InfluxDBClient,
    Point
)

from influxdb_client.client.write_api import (
    SYNCHRONOUS
)

from config import (
    DEVICE_ID,
    INFLUX_URL,
    INFLUX_TOKEN,
    INFLUX_ORG,
    INFLUX_BUCKET,
    check_config
)


# =====================================================
# CONFIG
# =====================================================

check_config()


# =====================================================
# THƯ MỤC OUTPUT
# =====================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = ROOT_DIR / "output"

OUTPUT_DIR.mkdir(
    exist_ok=True
)


# =====================================================
# INFLUXDB
# =====================================================

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

query_api = client.query_api()

write_api = client.write_api(
    write_options=SYNCHRONOUS
)


# =====================================================
# ĐỌC SENSOR_RAW
# =====================================================

def load_raw_data():

    print()
    print("====================================")
    print("DANG DOC sensor_raw TU INFLUXDB")
    print("====================================")

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -24h)

      |> filter(
          fn: (r) =>
          r["_measurement"] == "sensor_raw"
      )

      |> filter(
          fn: (r) =>
          r["device_id"] == "{DEVICE_ID}"
      )

      |> filter(
          fn: (r) =>
          r["_field"] == "temperature"
          or r["_field"] == "humidity"
          or r["_field"] == "distance_cm"
      )
    '''

    result = query_api.query_data_frame(
        query
    )

    # query_data_frame có thể trả về list
    if isinstance(result, list):

        frames = [
            frame
            for frame in result
            if not frame.empty
        ]

        if not frames:
            return pd.DataFrame()

        result = pd.concat(
            frames,
            ignore_index=True
        )

    if result.empty:
        return pd.DataFrame()

    print(
        "So dong doc tu InfluxDB:",
        len(result)
    )

    # Chuyển field thành cột
    df = result.pivot_table(
        index="_time",
        columns="_field",
        values="_value",
        aggfunc="last"
    )

    df.index = pd.to_datetime(
        df.index
    )

    df = df.sort_index()

    # Xóa timestamp bị trùng
    df = df[
        ~df.index.duplicated(
            keep="last"
        )
    ]

    # Ép kiểu numeric
    for column in [
        "temperature",
        "humidity",
        "distance_cm"
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# =====================================================
# PHÁT HIỆN OUTLIER BẰNG IQR
# =====================================================

def remove_outliers_iqr(
    df,
    column
):

    series = df[
        column
    ].dropna()

    if len(series) < 4:

        print(
            f"{column}: "
            "khong du du lieu de IQR"
        )

        return df

    q1 = series.quantile(
        0.25
    )

    q3 = series.quantile(
        0.75
    )

    iqr = q3 - q1

    # Dữ liệu gần như hằng
    if iqr == 0:

        print(
            f"{column}: IQR = 0 "
            "-> bo qua outlier"
        )

        return df

    lower = (
        q1 - 1.5 * iqr
    )

    upper = (
        q3 + 1.5 * iqr
    )

    mask = (
        (df[column] < lower)
        |
        (df[column] > upper)
    )

    count = int(
        mask.sum()
    )

    print()
    print(
        f"IQR - {column}"
    )

    print(
        f"Q1    = {q1:.2f}"
    )

    print(
        f"Q3    = {q3:.2f}"
    )

    print(
        f"IQR   = {iqr:.2f}"
    )

    print(
        f"Lower = {lower:.2f}"
    )

    print(
        f"Upper = {upper:.2f}"
    )

    print(
        f"Outlier = {count}"
    )

    # Thay outlier bằng NaN
    df.loc[
        mask,
        column
    ] = np.nan

    return df


# =====================================================
# PREPROCESS
# =====================================================

def preprocess_data(
    raw_df
):

    sensor_columns = [
        "temperature",
        "humidity",
        "distance_cm"
    ]

    columns = [
        column
        for column in sensor_columns
        if column in raw_df.columns
    ]

    df = raw_df[
        columns
    ].copy()

    # =================================================
    # 1. RAW DATA
    # =================================================

    print()
    print("====================================")
    print("1. RAW DATA")
    print("====================================")

    print(
        df.head(10)
    )

    print()

    print(
        "So mau raw:",
        len(df)
    )

    # Lưu raw CSV

    raw_file = (
        OUTPUT_DIR
        / "raw_data.csv"
    )

    df.to_csv(
        raw_file
    )

    print(
        "Da luu:",
        raw_file
    )

    # =================================================
    # 2. MISSING VALUES
    # =================================================

    print()
    print("====================================")
    print("2. MISSING VALUES - BEFORE")
    print("====================================")

    print(
        df.isna().sum()
    )

    # =================================================
    # 3. RESAMPLING 30 GIÂY
    # =================================================

    print()
    print("====================================")
    print("3. RESAMPLING 30 GIAY")
    print("====================================")

    df = (
        df
        .resample("30s")
        .mean()
    )

    print(
        "So mau sau resampling:",
        len(df)
    )

    print()
    print(
        df.head(10)
    )

    # =================================================
    # 4. XỬ LÝ MISSING
    # =================================================

    print()
    print("====================================")
    print("4. XU LY MISSING VALUES")
    print("====================================")

    print(
        "Missing truoc:"
    )

    print(
        df.isna().sum()
    )

    # Nội suy theo thời gian
    df = df.interpolate(
        method="time",
        limit_direction="both"
    )

    df = df.ffill()
    df = df.bfill()

    print()
    print(
        "Missing sau:"
    )

    print(
        df.isna().sum()
    )

    # =================================================
    # 5. OUTLIER IQR
    # =================================================

    print()
    print("====================================")
    print("5. OUTLIER DETECTION - IQR")
    print("====================================")

    for column in columns:

        df = remove_outliers_iqr(
            df,
            column
        )

    # Sau khi outlier thành NaN
    # nội suy lại
    df = df.interpolate(
        method="time",
        limit_direction="both"
    )

    df = df.ffill()
    df = df.bfill()

    # =================================================
    # 6. FEATURE ENGINEERING
    # =================================================

    print()
    print("====================================")
    print("6. FEATURE ENGINEERING")
    print("====================================")

    # Temperature
    if "temperature" in df.columns:

        df[
            "temperature_rolling_mean"
        ] = (
            df["temperature"]
            .rolling(
                window=3,
                min_periods=1
            )
            .mean()
        )

        df[
            "temperature_delta"
        ] = (
            df["temperature"]
            .diff()
            .fillna(0)
        )

    # Humidity
    if "humidity" in df.columns:

        df[
            "humidity_rolling_mean"
        ] = (
            df["humidity"]
            .rolling(
                window=3,
                min_periods=1
            )
            .mean()
        )

        df[
            "humidity_delta"
        ] = (
            df["humidity"]
            .diff()
            .fillna(0)
        )

    # Distance
    if "distance_cm" in df.columns:

        df[
            "distance_rolling_mean"
        ] = (
            df["distance_cm"]
            .rolling(
                window=3,
                min_periods=1
            )
            .mean()
        )

        df[
            "distance_delta"
        ] = (
            df["distance_cm"]
            .diff()
            .fillna(0)
        )

    # =================================================
    # 7. NORMALIZATION
    # =================================================

    print()
    print("====================================")
    print("7. MIN-MAX NORMALIZATION")
    print("====================================")

    normalize_columns = [
        column
        for column in [
            "temperature",
            "humidity",
            "distance_cm"
        ]
        if column in df.columns
    ]

    if normalize_columns:

        scaler = MinMaxScaler()

        scaled = scaler.fit_transform(
            df[
                normalize_columns
            ]
        )

        name_map = {
            "temperature":
                "temperature_norm",

            "humidity":
                "humidity_norm",

            "distance_cm":
                "distance_norm"
        }

        for index, column in enumerate(
            normalize_columns
        ):

            df[
                name_map[column]
            ] = (
                scaled[
                    :,
                    index
                ]
            )

    # =================================================
    # 8. CLEAN FINAL
    # =================================================

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    df = df.ffill()
    df = df.bfill()

    print()
    print(
        df.head(10)
    )

    print()
    print(
        "So mau processed:",
        len(df)
    )

    # Lưu CSV

    processed_file = (
        OUTPUT_DIR
        / "processed_data.csv"
    )

    df.to_csv(
        processed_file
    )

    print()
    print(
        "Da luu:",
        processed_file
    )

    return df


# =====================================================
# GHI SENSOR_PROCESSED VÀO INFLUXDB
# =====================================================

def save_processed_to_influx(
    df
):

    print()
    print("====================================")
    print("8. WRITE sensor_processed")
    print("====================================")

    count = 0

    for timestamp, row in (
        df.iterrows()
    ):

        point = (
            Point(
                "sensor_processed"
            )
            .tag(
                "device_id",
                DEVICE_ID
            )
            .time(
                timestamp.to_pydatetime()
            )
        )

        fields_count = 0

        for column in df.columns:

            value = row[
                column
            ]

            if pd.isna(
                value
            ):
                continue

            point = point.field(
                column,
                float(value)
            )

            fields_count += 1

        if fields_count == 0:
            continue

        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point
        )

        count += 1

    print(
        "So point da ghi:",
        count
    )

    print(
        "[SUCCESS] sensor_processed "
        "saved to InfluxDB"
    )


# =====================================================
# MAIN
# =====================================================

def main():

    print()
    print("====================================")
    print("BAI THUC HANH SO 2")
    print("IOT DATA PREPROCESSING")
    print("====================================")

    raw_df = load_raw_data()

    if raw_df.empty:

        print()
        print(
            "[ERROR] Khong tim thay "
            "du lieu sensor_raw."
        )

        print(
            "Hay kiem tra InfluxDB "
            "va bucket iot_data."
        )

        return

    processed_df = preprocess_data(
        raw_df
    )

    save_processed_to_influx(
        processed_df
    )

    print()
    print("====================================")
    print("PREPROCESSING COMPLETE")
    print("====================================")


if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        print()
        print(
            "[ERROR]",
            type(error).__name__,
            ":",
            error
        )

    finally:

        client.close()