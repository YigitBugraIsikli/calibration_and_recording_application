import json
import time
import asyncio
import websockets
import msgpack
import numpy as np
from PIL import Image
import base64
import os
from datetime import datetime
from io import BytesIO
import requests
import paho.mqtt.client as mqtt
from flask import Flask, request, jsonify

app = Flask(__name__)

CONFIG_FILE = 'config.json'
IMAGES_DATA_DIR = 'images_data'
HISTORY_FILE = 'history.json'

BASE_PATH = r'C:\Users\yigit\OneDrive\Masaüstü\python_application\save_images'
SESSION_ID = ""
CAMERA_IDS = []

#! ============================ MQTT Ayarları ============================


try:
    event_loop = asyncio.get_running_loop()
except RuntimeError:
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
# Değer listeleri ve eşik değerleri
pan_values = []
tilt_values = []
rgb_zoom_values = []
swir_1_zoom_values = []

stable_threshold = 15
stable_threshold_rgb_zoom = 5
stable_threshold_swir_1_zoom = 5

previous_distance_m = None

BROKER = "192.168.0.145"
PORT = 1883
TOPIC_lrf = "acikgoz/entity_state/acikgoz_lrf"
TOPIC_pantilt = "acikgoz/entity_state/acikgoz_pantilt"
TOPIC_RGB_ZOOM = "acikgoz/entity_state/cameradevice_rgb_1"
TOPIC_SWIR_1_ZOOM = "acikgoz/entity_state/cameradevice_swir_1"


def is_pan_tilt_stable():
    return (
        len(pan_values) == stable_threshold and
        len(set(pan_values)) == 1 and
        len(set(tilt_values)) == 1
    )


def is_rgb_zoom_stable():
    return len(rgb_zoom_values) == stable_threshold_rgb_zoom and len(set(rgb_zoom_values)) == 1


def is_swir_1_zoom_stable():
    return len(swir_1_zoom_values) == stable_threshold_swir_1_zoom and len(set(swir_1_zoom_values)) == 1


def wait_for_full_stability():
    """Tüm bileşenler stabil olana kadar bekler."""
    while not (is_pan_tilt_stable() and is_rgb_zoom_stable() and is_swir_1_zoom_stable()):
        time.sleep(0.1)
    print("Tüm sistemler stabil hale geldi!")


def on_message(client, userdata, msg):
    global previous_distance_m, pan_values, tilt_values, rgb_zoom_values, swir_1_zoom_values
    try:
        if msg.topic == TOPIC_lrf:
            data = json.loads(msg.payload.decode())
            distance_m = data['measured_distance_meters']

            if distance_m > 0 and distance_m != previous_distance_m:
                print(f"Distance changed to: {distance_m}")

                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                file_name = f"{timestamp}_{distance_m}.txt"

                global BASE_PATH, SESSION_ID, CAMERA_IDS
                if len(SESSION_ID) > 0:
                    for camera_id in CAMERA_IDS:
                        # Her kamera için ayrı klasör oluştur
                        save_dir = os.path.join(BASE_PATH, SESSION_ID, camera_id)
                        os.makedirs(save_dir, exist_ok=True)
                        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                        file_name = f"{timestamp}_{distance_m}.txt"               
                        file_path = os.path.join(save_dir, file_name)
                
                        with open(file_path, 'w') as f:
                            f.write(f"Measured distance: {distance_m} meters")
                        
                        print(f"File saved for {camera_id}: {file_path}")

                previous_distance_m = distance_m

        elif msg.topic == TOPIC_pantilt:
            data = json.loads(msg.payload.decode())
            pan_deg = data["pan_deg_x100"] / 100
            tilt_deg = data["tilt_deg_x100"] / 100

            pan_values.append(pan_deg)
            tilt_values.append(tilt_deg)

            if len(pan_values) > stable_threshold:
                pan_values.pop(0)
            if len(tilt_values) > stable_threshold:
                tilt_values.pop(0)

        elif msg.topic == TOPIC_RGB_ZOOM:
            data = json.loads(msg.payload.decode())
            rgb_zoom_deg = data["zoom_value"]

            rgb_zoom_values.append(rgb_zoom_deg)

            if len(rgb_zoom_values) > stable_threshold_rgb_zoom:
                rgb_zoom_values.pop(0)

        elif msg.topic == TOPIC_SWIR_1_ZOOM:
            data = json.loads(msg.payload.decode())
            swir_1_zoom_deg = data['zoom_lens_state']['zoom_step']

            swir_1_zoom_values.append(swir_1_zoom_deg)

            if len(swir_1_zoom_values) > stable_threshold_swir_1_zoom:
                swir_1_zoom_values.pop(0)

    except json.JSONDecodeError:
        print("Geçerli bir JSON mesajı alınamadı.")


mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.subscribe([(TOPIC_lrf, 0), (TOPIC_pantilt, 0), (TOPIC_RGB_ZOOM, 0), (TOPIC_SWIR_1_ZOOM, 0)])
mqtt_client.loop_start()

#! ============================ Yapılandırma ve Dosya İşlemleri ============================

def get_datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_config(new_config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(new_config, file, indent=4)

def save_log(request_data):
    ensure_directory(IMAGES_DATA_DIR)
    timestamp = get_timestamp()
    log_file = os.path.join(IMAGES_DATA_DIR, f"{timestamp}.txt")
    with open(log_file, 'w') as file:
        json.dump({"timestamp": timestamp, "request": request_data}, file, indent=4)

def save_to_history(new_request):
    history = {"requests": []}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as file:
                content = file.read().strip()
                history = json.loads(content) if content else history
        except json.JSONDecodeError:
            pass

    history["requests"].append(new_request)
    with open(HISTORY_FILE, 'w') as file:
        json.dump(history, file, indent=4)

def ensure_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_timestamp():
    """Şu anki zamanı timestamp formatında döndürür."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]

#! ============================ Görüntü İşleme İşlemleri ============================

def unpack_msgpack(message):
    """Mesajı msgpack formatından çözer."""
    try:
        return msgpack.unpackb(message, raw=False)
    except Exception as e:
        print(f"❌ Unpack hatası: {e}")
        return None

# 16-bit'ten 8-bit'e normalizasyon
def normalize_16bit_to_8bit(image_array):
    image_8bit = ((image_array - image_array.min()) / (image_array.max() - image_array.min()) * 255).astype(np.uint8)
    return image_8bit

def bytes_to_base64(byte_data):
    """Byte verisini base64 formatına dönüştürür."""
    return base64.b64encode(byte_data).decode("utf-8")

def process_and_save_image(pixels_data, width, height, directory, file_name_prefix):
    """Pikselleri işleyip görüntüyü kaydeder (16-bit veriyi 8-bit'e dönüştürerek)."""
    try:
        if not pixels_data or not width or not height:
            print("⚠️ Eksik veri alındı!")
            return False

        image_array = np.frombuffer(pixels_data, dtype=np.uint8)
        if len(image_array) != width * height:
            print("⚠️ Piksel verisi boyutu uyuşmuyor!")
            return False

        image_array = image_array.reshape((height, width))    
        # 16-bit'i 8-bit'e normalleştir
        image_array = normalize_16bit_to_8bit(image_array)
        image = Image.fromarray(image_array, mode="L")  # Grayscale 8-bit
        
        global BASE_PATH, SESSION_ID, CAMERA_IDS
        cam_path = os.path.join(BASE_PATH, SESSION_ID, file_name_prefix)
        file_name = get_datetime_str()
        file_name_full = os.path.join(cam_path, f'{file_name}.png')
        image.save(file_name_full, 'PNG')
        print(f"✅ Görüntü kaydedildi: {file_name_full}")
        
        return True
    except Exception as e:
        print(f"❌ Görüntü işlenirken hata oluştu: {e}")
        return False

def process_and_save_lwir(pixels_data, width, height, directory, file_name_prefix):
    """Pikselleri işleyip görüntüyü kaydeder (16-bit veriyi 8-bit'e dönüştürerek)."""
    try:
        if not pixels_data or not width or not height:
            print("⚠️ Eksik veri alındı!")
            return False
        image_array = np.frombuffer(pixels_data, dtype=np.uint16)
        if len(image_array) != width * height:
            print("⚠️ Piksel verisi boyutu uyuşmuyor!")
            return False
        image_array = image_array.reshape((height, width))    
        # 16-bit'i 8-bit'e normalleştir
        image_array = normalize_16bit_to_8bit(image_array)
        image = Image.fromarray(image_array, mode="L")  # Grayscale 8-bit

        ensure_directory(directory)
        file_name = os.path.join(directory, f"{file_name_prefix}_{get_timestamp()}.png")
        image.save(file_name, 'PNG')
        print(f"✅ Görüntü kaydedildi: {file_name}")
        return True
    except Exception as e:
        print(f"❌ Görüntü işlenirken hata oluştu: {e}")
        return False
    
#! ============================ Buffer İşlemleri============================

    
def process_buffer(buffer, session_timestamp):
    saved_cameras = set()

    for camera_frames in buffer:
        device_id = camera_frames.get("device_id", "").strip()       
        
        base_directory = f"save_images/{device_id}"
        global BASE_PATH, SESSION_ID, CAMERA_IDS
        session_directory = os.path.join(BASE_PATH, SESSION_ID)

        if device_id in ["cameradevice_vnir_playerone", "cameradevice_rgb_1"]:
            if "image_data" in camera_frames and "pixels" in camera_frames["image_data"]:
                cleaned_data = bytes_to_base64(camera_frames["image_data"]["pixels"])
                image_data = base64.b64decode(cleaned_data)
                image = Image.open(BytesIO(image_data))
                cam_path = os.path.join(BASE_PATH, SESSION_ID, device_id)
                file_name = get_datetime_str()
                file_name_full = os.path.join(cam_path, f"{file_name}.jpg")
                try:
                    image.save(file_name_full, 'JPEG')
                except Exception:
                    continue
                print(f"✅ Görüntü kaydedildi: {file_name_full}")
                saved_cameras.add(device_id)

        elif device_id == "cameradevice_swir_1":
            image_data = camera_frames.get("image_data", {})
            success = process_and_save_image(image_data.get("pixels", b""), image_data.get("width"), image_data.get("height"), session_directory, device_id)
            if success:
                saved_cameras.add(device_id)
                
        elif device_id == "cameradevice_lwir_1":
            image_data = camera_frames.get("image_data", {})
            success = process_and_save_lwir(image_data.get("pixels", b""), image_data.get("width"), image_data.get("height"), session_directory, device_id)
            if success:
                saved_cameras.add(device_id)


    print(f"🎯 {len(saved_cameras)} farklı kamera verisi işlendi.")

#! ============================ WebSocket İşlemleri ============================

async def websocket_baglan(duration_second, request_data):  
    url = "ws://192.168.0.145:10000"
    total_duration = duration_second  
    start_time = time.time()
    
    session_timestamp = get_timestamp()

    buffer = []  
    
    try:
        async with websockets.connect(url, max_size=20*1024*1024) as ws:
            print("✅ WebSocket bağlantısı başarılı!")
            while time.time() - start_time < total_duration:
                try:
                    message = await ws.recv()
                    unpacked_message = unpack_msgpack(message)

                    if not (unpacked_message and isinstance(unpacked_message, list) and len(unpacked_message) > 0):
                        continue
                    data = unpacked_message[0]
                    frame = data['camera_frames'][0]
                    # camera_frames = unpacked_message[0].get("camera_frame", {})    
                    # Gelen verileri buffer'a ekle
                    buffer.append(frame)
                    await ws.send("received")
                except Exception as e:
                    print(f"❌ Veri alma hatası: {e}")
            print("Total time elapsed!")
            print (f"Total frame count: {len(buffer)}")
            await ws.close()
    
    except Exception as e:
        print(f"❌ WebSocket bağlantı hatası: {e}")

    # Bağlantıyı kapattıktan sonra buffer'daki verileri işle
    print(f"📥 Toplam {len(buffer)} görüntü verisi alındı, işleniyor...")
    process_buffer(buffer, session_timestamp)

    save_log(request_data)  

#! ============================ API İşlemleri ============================


app = Flask(__name__)

INVOKE_URL = "http://192.168.0.106:8080/api/1.0/invoke"


@app.route('/process-requests', methods=['POST'])
async def process_requests():
    """İstekleri sırayla işleyip hedef URL'ye gönderir ve history.json'a kaydeder."""
    incoming_data = request.get_json()

    if "requests" not in incoming_data:
        return jsonify({"error": "'requests' key is required in the incoming data"}), 400

    results = []
    for idx, req in enumerate(incoming_data["requests"]):
        save_to_history(req)

        try:
            response = requests.post(INVOKE_URL, json=req)

            if response.status_code == 204 or not response.text.strip():
                response_data = {"message": "No Content", "status_code": 204}
            else:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = {"error": "Invalid JSON response", "raw_response": response.text}

            results.append({
                "request": req,
                "response": response_data,
                "status_code": response.status_code
            })

            print(f"✅ {req['command_id']} işlemi başarıyla gönderildi!")

            duration_second = req.get("args", {}).get("duration_second", 0)
            if duration_second > 0:
                global SESSION_ID, CAMERA_IDS, BASE_PATH
                SESSION_ID = time.strftime("%Y-%m-%d_%H-%M-%S")
                CAMERA_IDS = req.get('args').get('camera_ids')
                session_path = os.path.join(BASE_PATH, SESSION_ID)
                for cam in CAMERA_IDS:
                    cam_path = os.path.join(session_path, cam)
                    os.makedirs(cam_path)
                
                wait_for_full_stability()
                await websocket_baglan(duration_second=duration_second, request_data=req)

        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP isteği başarısız: {e}")
            results.append({"request": req, "error": str(e)})
            

    return jsonify({"message": "Requests processed", "results": results})

if __name__ == '__main__':
    app.run(debug=True)
