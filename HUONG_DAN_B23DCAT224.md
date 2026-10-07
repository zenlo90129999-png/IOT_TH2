# Hướng dẫn chạy trên Windows – B23DCAT224

## Chuẩn bị
- VS Code, extension PlatformIO IDE và Wokwi Simulator. Kích hoạt license Wokwi cho VS Code theo https://docs.wokwi.com/vscode/getting-started .
- Python 3 (có pip). Tạo môi trường ảo mới trên máy bạn.
- InfluxDB OSS 2.x. Nếu chạy qua Docker thì cần Docker Desktop đang hoạt động.
- Internet để tải thư viện, chạy Wokwi, kết nối MQTT và đồng bộ NTP.
- Git và tài khoản GitHub để nộp mã nguồn theo đề.
- Mô phỏng có ESP32, DHT22, HC-SR04 và LED trong diagram.json. Nếu giảng viên yêu cầu phần cứng thật, cần triển khai lên thiết bị thật.

## 1. Mở dự án và cài thư viện Python
Giải nén vào thư mục mới. VS Code > Open Folder > chọn thư mục chứa platformio.ini.
Mở terminal PowerShell ở thư mục đó:

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Không cần kích hoạt môi trường khi gọi trực tiếp python.exe như trên.
PlatformIO tự tải nền tảng ESP32, PubSubClient và DHTesp theo platformio.ini khi build.

## 2. Chạy InfluxDB 2.x
Nếu chưa có InfluxDB, cài và mở Docker Desktop, sau đó chạy một lần:

```powershell
docker run -d --name influxdb-iot -p 8086:8086 -v influxdb-iot-data:/var/lib/influxdb2 -v influxdb-iot-config:/etc/influxdb2 influxdb:2
```

Những lần sau dùng `docker start influxdb-iot`.
Nếu đã chạy InfluxDB 2.x trên cổng 8086 thì dùng instance đó, không tạo container thứ hai cùng cổng.
Mở http://localhost:8086, tạo tài khoản, organization PTIT, bucket iot_data.
Đặt retention cho bucket (ví dụ 7 ngày để demo; đây là lựa chọn, không phải con số bắt buộc trong đề).
Tạo token có quyền đọc/ghi bucket iot_data, điền vào INFLUX_TOKEN trong .env.
.env hiện giữ token từ bản gửi lên; nếu là máy/cơ sở dữ liệu khác phải thay bằng token của bạn.
Không đưa .env lên GitHub. .env.example là mẫu không chứa token thật.

## 3. Kiểm tra mã sinh viên
Firmware và Python đã thống nhất:
- Topic: ptit/iot/B23DCAT224/esp32/sensor
- Device ID: ESP32-B23DCAT224
- MQTT broker đang cấu hình: broker.emqx.io:1883
Không cần cài broker riêng nếu dùng broker công cộng này và kết nối được.
Dữ liệu cũ trong InfluxDB không tự đổi mã; hãy thu thập dữ liệu mới.

## 4. Build và khởi động
1. Trong VS Code chạy PlatformIO: Build (hoặc pio run trong PlatformIO terminal).
2. Chạy collector ở một terminal và giữ nó hoạt động:

```powershell
.\venv\Scripts\python.exe python\mqtt_to_influx.py
```

3. F1 > Wokwi: Start Simulator. Chờ kết nối Wi-Fi, NTP, MQTT; firmware gửi mỗi 5 giây. Giữ tab mô phỏng hiển thị.
4. Thay đổi cảm biến, thu thập vài phút. Ở terminal khác chạy:

```powershell
.\venv\Scripts\python.exe python\preprocess.py
.\venv\Scripts\python.exe -m streamlit run python\dashboard.py
```

5. Mở http://localhost:8501. Dashboard tự làm mới, nhưng preprocess.py chỉ xử lý một lượt. Chạy lại script tiền xử lý khi cần cập nhật sensor_processed.
Nếu cần kiểm tra riêng MQTT: `.\venv\Scripts\python.exe python\mqtt_test.py` (giữ mô phỏng đang chạy).
`test_influx.py` kiểm tra sức khỏe dịch vụ, không chứng minh token có quyền đọc/ghi bucket.

## 5. Hoàn thành bài thực hành
- Chứng minh thu thập/validate và ghi sensor_raw hoạt động.
- Cấu hình retention; thử mất bản tin, trùng lặp, thiết bị khởi động lại.
- Chứng minh missing values, IQR, resampling 30 giây, rolling mean, delta và Min-Max; lưu sensor_processed.
- Chụp dashboard dữ liệu mới và ghi số liệu đo thực tế.
- latency_ms hiện là thời gian từ timestamp thiết bị đến lúc collector nhận, chưa bao gồm toàn bộ thời gian ghi DB/hiển thị dashboard. Cần mô tả đúng phạm vi đo; đồng bộ đồng hồ để kết quả có ý nghĩa.
- Đánh giá hiệu năng/lưu trữ và viết báo cáo Word 4–6 trang theo đề, nộp mã nguồn GitHub và app.
- CSV trong output là dữ liệu mẫu cũ được giữ nguyên, không phải kết quả thực nghiệm mới của B23DCAT224. Chạy preprocess.py sẽ ghi lại bằng dữ liệu mới.

## Ghi chú bản sửa
Đã đổi B23DCAT289 thành B23DCAT224 trong firmware, cấu hình, collector client ID, script kiểm tra MQTT và README; bổ sung .env.example và hướng dẫn này.
Không đóng gói lại venv và cache/firmware build cũ; chúng cần được tạo lại trên máy đích. Chưa chạy kiểm thử tích hợp với Wokwi/InfluxDB của bạn.

Nguồn hướng dẫn công cụ:
- https://docs.wokwi.com/vscode/platformio
- https://docs.influxdata.com/influxdb/v2/install/
