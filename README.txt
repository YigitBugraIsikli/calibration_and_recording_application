# Python WebSocket & MQTT Tabanlı Kamera ve Pan-Tilt Kontrol Sistemi

Bu proje, birden fazla kameradan gelen görüntüleri WebSocket üzerinden alıp işleyerek, belirli bir dizine kaydeden bir Python uygulamasıdır.
Ayrıca, MQTT üzerinden pan-tilt kontrolü sağlayarak cihazın hareket durumunu izler.

## Özellikler
- **WebSocket Bağlantısı:** Kameralardan gelen görüntüleri gerçek zamanlı olarak alır ve işler.
- **MQTT Entegrasyonu:** Pan-tilt cihazının hareket durumunu, RGB ve SWIR kamera için zoom durumunu takip eder ve stabil hale geldiğinde işlemi tamamlar.
- **Görüntü İşleme:** Alınan ham görüntüleri işleyerek uygun formatta kaydeder.
- **Dinamik Klasör Yapısı:** Her kayıt oturumu için yeni bir klasör oluşturur ve ilgili kamera verilerini düzenli olarak saklar.
- **API Entegrasyonu:** Gelen JSON isteklerini bir APIye yönlendirir ve cevapları kaydeder.
- **Buffer Kullanımı:** Kayıt süresince tüm görüntüleri bir bellekte toplar ve ardından kaydederek performans artışı sağlar.

## Yapılandırma Dosyaları
- `config.json`: Uygulamanın en son yapılandırmasını içerir.
- `history.json`: Geçmişte işlenen istekleri saklar.
- `images_data/`: Görüntü datalarının saklandığı klasör.
- `save_images/`: Kaydedilen görüntülerin saklandığı ana klasör.

## Kullanım
1. '**Bağımlılıkları Kurun:**'
   ```bash
   pip install asyncio websockets msgpack numpy pillow requests paho-mqtt flask opencv-python

2. ' Uygulamayı çalıştırın'
    python application.py 

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

## API Örnek Kullanımı

    ==>  POSTMAN  <==

- 'Request Type': POST
- 'Url':  " http://192.168.0.145:5000/process-request "
- 'Headers' ==>  'Key': Content-Type | 'Value': application/json
- 'Body': 

{
    "requests": [
        {
            "target_id": "camera_device",
            "device_id": "acikgoz_pantilt",
            "command_id": "start_recording_command",
            "args": {
                "duration_second": x,
                "camera_ids" : ["cameradevice_swir_1", "cameradevice_rgb_1"]
            }
        },
        {   
            "target_id" : "entity",
            "device_id" : "acikgoz_pantilt",
            "command_id" : "set_pan_position_degree",
            "args" : {
                "pan_position_deg_x100" : xxxxx
            }
        },
        {
            "target_id": "entity",
            "device_id": "acikgoz_pantilt",
            "command_id": "set_tilt_position_degree",
            "args": {
                "tilt_position_deg_x100": xxx
            }
        }
    ]
}

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    ==> Powershell Curl ile <== 

Invoke-WebRequest -Uri "http://127.0.0.1:5000/process-requests" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{
    "requests": [
        {
            "target_id": "camera_device",
            "device_id": "acikgoz_pantilt",
            "command_id": "start_recording_command",
            "args": {
                "duration_second": x,
                "camera_ids" : ["cameradevice_swir_1", "cameradevice_rgb_1"]
            }
        },
        {   
            "target_id" : "entity",
            "device_id" : "acikgoz_pantilt",
            "command_id" : "set_pan_position_degree",
            "args" : {
                "pan_position_deg_x100" : xxxxx
            }
        },
        {
            "target_id": "entity",
            "device_id": "acikgoz_pantilt",
            "command_id": "set_tilt_position_degree",
            "args": {
                "tilt_position_deg_x100": xxx
            }
        }
    ]
}'