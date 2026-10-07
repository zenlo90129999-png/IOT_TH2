from influxdb_client import InfluxDBClient

from config import (
    INFLUX_URL,
    INFLUX_TOKEN,
    INFLUX_ORG
)


client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

health = client.health()

print("Status :", health.status)
print("Message:", health.message)

client.close()