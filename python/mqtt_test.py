import paho.mqtt.client as mqtt


BROKER = "broker.emqx.io"
PORT = 1883

TOPIC = "ptit/iot/B23DCAT224/esp32/sensor"


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):
    print("==============================")
    print("PYTHON MQTT CONNECTED")
    print("Broker:", BROKER)
    print("Topic :", TOPIC)
    print("Code  :", reason_code)
    print("==============================")

    client.subscribe(TOPIC)


def on_message(
    client,
    userdata,
    msg
):
    print()
    print("========== RECEIVED ==========")
    print("Topic:")

    print(msg.topic)

    print("Payload:")

    print(
        msg.payload.decode("utf-8")
    )

    print("==============================")


client = mqtt.Client(
    callback_api_version=
        mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message


print("Connecting to MQTT...")

client.connect(
    BROKER,
    PORT,
    60
)

client.loop_forever()