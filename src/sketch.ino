#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <time.h>
#include <sys/time.h>

// ===============================
// DEVICE
// ===============================

const char* DEVICE_ID =
    "ESP32-B23DCAT224";

// ===============================
// WIFI
// ===============================

const char* WIFI_SSID =
    "Wokwi-GUEST";

const char* WIFI_PASSWORD =
    "";

// ===============================
// MQTT
// ===============================

const char* MQTT_SERVER =
    "broker.emqx.io";

const int MQTT_PORT = 1883;

const char* MQTT_TOPIC =
    "ptit/iot/B23DCAT224/esp32/sensor";

// ===============================
// GPIO
// ===============================

const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN = 2;

// Gửi dữ liệu 5 giây/lần
const unsigned long SEND_INTERVAL_MS =
    5000;

// ===============================

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

DHTesp dht;

unsigned long lastSend = 0;
unsigned long sequenceNo = 0;


// ===============================
// WIFI CONNECT
// ===============================

void connectWiFi() {

    Serial.println();
    Serial.println("Connecting WiFi...");

    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD,
        6
    );

    while (
        WiFi.status()
        != WL_CONNECTED
    ) {

        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("WiFi CONNECTED");

    Serial.print("IP: ");
    Serial.println(
        WiFi.localIP()
    );

    Serial.print("RSSI: ");
    Serial.print(
        WiFi.RSSI()
    );

    Serial.println(" dBm");
}


// ===============================
// NTP
// ===============================

void syncTime() {

    Serial.println(
        "Synchronizing time..."
    );

    configTime(
        0,
        0,
        "pool.ntp.org",
        "time.google.com"
    );

    time_t now = time(nullptr);

    int retry = 0;

    while (
        now < 1700000000
        &&
        retry < 30
    ) {

        delay(500);
        Serial.print(".");

        now = time(nullptr);

        retry++;
    }

    Serial.println();

    if (
        now >= 1700000000
    ) {

        Serial.println(
            "NTP synchronized"
        );

    } else {

        Serial.println(
            "NTP sync failed"
        );
    }
}


// ===============================
// UNIX TIME MILLISECOND
// ===============================

unsigned long long getEpochMs() {

    struct timeval tv;

    gettimeofday(
        &tv,
        nullptr
    );

    return
        (unsigned long long)tv.tv_sec
        * 1000ULL
        +
        (unsigned long long)tv.tv_usec
        / 1000ULL;
}


// ===============================
// MQTT CONNECT
// ===============================

void connectMQTT() {

    while (
        !mqttClient.connected()
    ) {

        Serial.println();
        Serial.println(
            "Connecting MQTT..."
        );

        Serial.print(
            "Broker: "
        );

        Serial.println(
            MQTT_SERVER
        );

        String clientId =
            "ESP32-B23DCAT224-";

        clientId += String(
            random(0xffff),
            HEX
        );

        if (
            mqttClient.connect(
                clientId.c_str()
            )
        ) {

            Serial.println(
                "MQTT CONNECTED"
            );

        } else {

            Serial.print(
                "MQTT FAILED rc="
            );

            Serial.println(
                mqttClient.state()
            );

            delay(2000);
        }
    }
}


// ===============================
// HC-SR04
// ===============================

float readDistanceCm() {

    digitalWrite(
        TRIG_PIN,
        LOW
    );

    delayMicroseconds(2);

    digitalWrite(
        TRIG_PIN,
        HIGH
    );

    delayMicroseconds(10);

    digitalWrite(
        TRIG_PIN,
        LOW
    );

    unsigned long duration =
        pulseIn(
            ECHO_PIN,
            HIGH,
            30000
        );

    if (
        duration == 0
    ) {

        return NAN;
    }

    return
        duration
        * 0.0343f
        / 2.0f;
}


// ===============================
// SENSOR VALIDATION
// ===============================

bool validSensorData(
    float temperature,
    float humidity,
    float distance
) {

    if (
        !isfinite(temperature)
        ||
        !isfinite(humidity)
        ||
        !isfinite(distance)
    ) {

        return false;
    }

    if (
        temperature < -40
        ||
        temperature > 80
    ) {

        return false;
    }

    if (
        humidity < 0
        ||
        humidity > 100
    ) {

        return false;
    }

    if (
        distance < 2
        ||
        distance > 400
    ) {

        return false;
    }

    return true;
}


// ===============================
// PUBLISH
// ===============================

void publishData() {

    TempAndHumidity data =
        dht.getTempAndHumidity();

    float distance =
        readDistanceCm();

    if (
        !validSensorData(
            data.temperature,
            data.humidity,
            distance
        )
    ) {

        Serial.println(
            "Invalid sensor data"
        );

        return;
    }

    sequenceNo++;

    unsigned long uptime =
        millis() / 1000;

    unsigned long long ts =
        getEpochMs();

    int rssi =
        WiFi.RSSI();

    char payload[512];

    snprintf(
        payload,
        sizeof(payload),

        "{"
        "\"device_id\":\"%s\","
        "\"temperature\":%.2f,"
        "\"humidity\":%.2f,"
        "\"distance_cm\":%.2f,"
        "\"rssi\":%d,"
        "\"sequence\":%lu,"
        "\"uptime_s\":%lu,"
        "\"ts_ms\":%llu"
        "}",

        DEVICE_ID,

        data.temperature,
        data.humidity,
        distance,

        rssi,
        sequenceNo,
        uptime,
        ts
    );

    bool ok =
        mqttClient.publish(
            MQTT_TOPIC,
            payload
        );

    Serial.println();
    Serial.println(
        "========== SENSOR =========="
    );

    Serial.print(
        "Temperature : "
    );
    Serial.println(
        data.temperature
    );

    Serial.print(
        "Humidity    : "
    );
    Serial.println(
        data.humidity
    );

    Serial.print(
        "Distance    : "
    );
    Serial.println(
        distance
    );

    Serial.print(
        "RSSI        : "
    );
    Serial.println(
        rssi
    );

    Serial.print(
        "Sequence    : "
    );
    Serial.println(
        sequenceNo
    );

    Serial.print(
        "Uptime      : "
    );
    Serial.println(
        uptime
    );

    Serial.print(
        "Timestamp   : "
    );
    Serial.println(
        ts
    );

    Serial.print(
        "JSON        : "
    );
    Serial.println(
        payload
    );

    Serial.print(
        "Publish     : "
    );

    Serial.println(
        ok ? "OK" : "FAILED"
    );

    if (ok) {

        digitalWrite(
            LED_PIN,
            HIGH
        );

        delay(80);

        digitalWrite(
            LED_PIN,
            LOW
        );
    }
}


// ===============================
// SETUP
// ===============================

void setup() {

    Serial.begin(115200);

    delay(1000);

    Serial.println();
    Serial.println("==========================");
    Serial.println("ESP32 BOOT OK");
    Serial.println("==========================");

    pinMode(
        TRIG_PIN,
        OUTPUT
    );

    pinMode(
        ECHO_PIN,
        INPUT
    );

    pinMode(
        LED_PIN,
        OUTPUT
    );

    dht.setup(
        DHT_PIN,
        DHTesp::DHT22
    );

    connectWiFi();

    syncTime();

    mqttClient.setServer(
        MQTT_SERVER,
        MQTT_PORT
    );

    mqttClient.setBufferSize(
        512
    );
}


// ===============================
// LOOP
// ===============================

void loop() {

    if (
        WiFi.status()
        != WL_CONNECTED
    ) {

        connectWiFi();
        syncTime();
    }

    if (
        !mqttClient.connected()
    ) {

        connectMQTT();
    }

    mqttClient.loop();

    unsigned long now =
        millis();

    if (
        now - lastSend
        < SEND_INTERVAL_MS
    ) {

        return;
    }

    lastSend = now;

    publishData();
}