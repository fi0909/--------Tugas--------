from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json
import os
import paho.mqtt.client as mqtt
import threading

app = Flask(__name__)

MQTT_BROKER = "192.168.0.100"
MQTT_PORT = 1883

# MQTT rooms and devices configuration
MQTT_ROOMS = ["kamar1", "kamar2", "kamar3", "dapur", "ruang_cuci"]
MQTT_DEVICES = {
    "lampu": "lampu",
    "mesin_cuci": "mesinCuci",
    "pompa_air": "pompa",
    "kompor": "kompor",
}

house_data = {
    'status': 'kosong',  # kosong or berpenghuni - auto-detected via MQTT
    'mqtt_connected': False,
    'presence': {room: 0 for room in MQTT_ROOMS},  # 0 = no presence, 1 = presence detected
    'rooms': {
        'kamar1': {'name': 'Kamar 1', 'light': False, 'occupied': False},
        'kamar2': {'name': 'Kamar 2', 'light': False, 'occupied': False},
        'kamar3': {'name': 'Kamar 3', 'light': False, 'occupied': False},
        'dapur': {'name': 'Dapur', 'light': False, 'occupied': False},
        'ruang_cuci': {'name': 'Ruang Cuci Baju', 'light': False, 'occupied': False},
    },
    'devices': {
        'mesin_cuci': {'name': 'Mesin Cuci', 'status': False, 'icon': '🔄'},
        'pompa_air': {'name': 'Pompa Air', 'status': False, 'icon': '💧'},
        'kompor': {'name': 'Kompor', 'status': False, 'icon': '🔥'},
    },
    'notifications': [],
    'logs': [],
    'notification_sound_active': None
}

mqtt_client = None

def mqtt_on_connect(client, userdata, flags, rc):
    """Callback when MQTT client connects"""
    if rc == 0:
        print(f"[MQTT] Connected successfully (code: {rc})")
        house_data['mqtt_connected'] = True
        
        # Subscribe to all PIR sensors
        for room in MQTT_ROOMS:
            client.subscribe(f"smarthome/deteksi/{room}")
        
        # Subscribe to all device topics
        for room in MQTT_ROOMS:
            for device in MQTT_DEVICES:
                client.subscribe(f"smarthome/{room}/{MQTT_DEVICES[device]}")
        
        # Subscribe to global lock
        client.subscribe("smarthome/lock")
        
        add_log('Sistem', 'Terhubung ke MQTT Broker')
        print("[MQTT] Subscribed to all topics")
    else:
        print(f"[MQTT] Connection failed (code: {rc})")
        house_data['mqtt_connected'] = False

def mqtt_on_message(client, userdata, msg):
    """Callback when MQTT message is received"""
    topic = msg.topic
    payload = msg.payload.decode()
    
    try:
        for room in MQTT_ROOMS:
            if topic == f"smarthome/deteksi/{room}":
                presence_value = int(payload)
                house_data['presence'][room] = presence_value
                
                # Update global lock based on any room presence
                update_global_lock()
                print(f"[MQTT] PIR {room}: {presence_value}")
                return
        
        # Format: smarthome/{room}/{device}
        for room in MQTT_ROOMS:
            for device_key, device_mqtt in MQTT_DEVICES.items():
                if topic == f"smarthome/{room}/{device_mqtt}":
                    # You can add device status monitoring here if needed
                    print(f"[MQTT] Device update {room}/{device_mqtt}: {payload}")
                    return
    
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")

def update_global_lock():
    """Update house status based on PIR presence from any room"""
    if any(house_data['presence'].values()):
        new_status = 'berpenghuni'
    else:
        new_status = 'kosong'
    
    # Update status if changed
    if house_data['status'] != new_status:
        old_status = house_data['status']
        house_data['status'] = new_status
        add_log('Deteksi Kehadiran', f'Status berubah: {old_status} → {new_status}')
        
        # Auto-disable turn off buttons when berpenghuni
        if new_status == 'berpenghuni':
            add_notification('info', f'🚨 Orang terdeteksi di rumah!')
        else:
            add_notification('info', f'✓ Rumah kosong')

def send_mqtt_command(room, device, state):
    """Send command to device via MQTT"""
    if not mqtt_client or not house_data['mqtt_connected']:
        print("[MQTT] Not connected to broker")
        return False
    
    if room not in MQTT_ROOMS:
        print(f"[MQTT] Invalid room: {room}")
        return False
    
    if device not in MQTT_DEVICES:
        print(f"[MQTT] Invalid device: {device}")
        return False
    
    val = "1" if state == "on" else "0"
    topic = f"smarthome/{room}/{MQTT_DEVICES[device]}/perintah"
    
    mqtt_client.publish(topic, val)
    print(f"[MQTT] Command sent: {topic} → {val}")
    return True

def init_mqtt():
    """Initialize MQTT client"""
    global mqtt_client
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = mqtt_on_connect
        mqtt_client.on_message = mqtt_on_message
        
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Attempting to connect to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] Failed to initialize: {e}")
        house_data['mqtt_connected'] = False

def add_log(action, details):
    """Tambah log aktivitas"""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
        'details': details
    }
    house_data['logs'].append(log_entry)
    if len(house_data['logs']) > 100:
        house_data['logs'] = house_data['logs'][-100:]

def check_anomalies():
    """Check for anomalies and add notifications"""
    house_data['notifications'] = []
    
    # Check for lights on when house is empty
    if house_data['status'] == 'kosong':
        for room_id, room_data in house_data['rooms'].items():
            if room_data['light']:
                house_data['notifications'].append({
                    'id': len(house_data['notifications']) + 1,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': 'warning',
                    'message': f'💡 Lampu di {room_data["name"]} masih nyala padahal rumah kosong!',
                    'sound_type': 'light'
                })
    
    # Check for devices on when house is empty
    if house_data['status'] == 'kosong':
        for device_id, device_data in house_data['devices'].items():
            if device_data['status']:
                house_data['notifications'].append({
                    'id': len(house_data['notifications']) + 1,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': 'danger',
                    'message': f'⚙️ {device_data["name"]} masih aktif padahal rumah kosong!',
                    'sound_type': 'device'
                })

def add_notification(type, message, sound_type=None):
    """Tambah notifikasi"""
    notification = {
        'id': len(house_data['notifications']) + 1,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': type,
        'message': message,
        'sound_type': sound_type
    }
    house_data['notifications'].append(notification)
    if len(house_data['notifications']) > 10:
        house_data['notifications'] = house_data['notifications'][-10:]

@app.route('/')
def index():
    """Render halaman utama"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get status rumah"""
    check_anomalies()
    return jsonify({
        'status': house_data['status'],
        'mqtt_connected': house_data['mqtt_connected'],
        'room_count': len(house_data['rooms']),
        'active_lights': sum(1 for r in house_data['rooms'].values() if r['light']),
        'active_devices': sum(1 for d in house_data['devices'].values() if d['status']),
    })

@app.route('/api/rooms')
def get_rooms():
    """Get status semua ruangan"""
    return jsonify(house_data['rooms'])

@app.route('/api/devices')
def get_devices():
    """Get status semua perangkat"""
    return jsonify(house_data['devices'])

@app.route('/api/logs')
def get_logs():
    """Get activity logs"""
    return jsonify(house_data['logs'])

@app.route('/api/notifications')
def get_notifications():
    """Get notifikasi"""
    return jsonify(house_data['notifications'])

@app.route('/api/room/<room_id>/toggle', methods=['POST'])
def toggle_room_light(room_id):
    """Toggle lampu di ruangan"""
    if room_id not in house_data['rooms']:
        return jsonify({'error': 'Room not found'}), 404
    
    room = house_data['rooms'][room_id]
    current_state = room['light']
    
    if house_data['status'] == 'berpenghuni' and current_state:
        add_notification('warning', f'Lampu {room["name"]} tidak bisa dimatikan saat ada penghuni')
        return jsonify({'error': 'Cannot turn off lights when occupied'}), 403
    
    room['light'] = not current_state
    
    action = 'Menyalakan' if room['light'] else 'Mematikan'
    add_log('Kontrol Lampu', f'{action} lampu {room["name"]}')
    
    if room['light'] and house_data['status'] == 'kosong':
        add_notification('warning', f'💡 Lampu {room["name"]} menyala saat rumah kosong!', 'light')
    
    check_anomalies()
    return jsonify({'room_id': room_id, 'light': room['light']})

@app.route('/api/room/<room_id>/occupied', methods=['POST'])
def set_room_occupied(room_id):
    """Set room occupied status"""
    if room_id not in house_data['rooms']:
        return jsonify({'error': 'Room not found'}), 404
    
    data = request.get_json()
    occupied = data.get('occupied', False)
    
    house_data['rooms'][room_id]['occupied'] = occupied
    
    status = 'ditempati' if occupied else 'kosong'
    add_log('Status Ruangan', f'{house_data["rooms"][room_id]["name"]} menjadi {status}')
    
    return jsonify({'room_id': room_id, 'occupied': occupied})

@app.route('/api/lights/all/off', methods=['POST'])
def turn_off_all_lights():
    """Matikan semua lampu (hanya saat rumah kosong)"""
    if house_data['status'] == 'berpenghuni':
        add_notification('warning', 'Tidak bisa matikan semua lampu saat ada penghuni')
        return jsonify({'error': 'Cannot turn off all lights when occupied'}), 403
    
    for room_id, room in house_data['rooms'].items():
        room['light'] = False
    
    add_log('Kontrol Lampu', 'Mematikan semua lampu')
    add_notification('info', '✓ Semua lampu telah dimatikan')
    
    return jsonify({'message': 'All lights turned off'})

@app.route('/api/device/<device_id>/toggle', methods=['POST'])
def toggle_device(device_id):
    """Toggle perangkat"""
    if device_id not in house_data['devices']:
        return jsonify({'error': 'Device not found'}), 404
    
    device = house_data['devices'][device_id]
    device['status'] = not device['status']
    
    action = 'Menyalakan' if device['status'] else 'Mematikan'
    add_log('Kontrol Perangkat', f'{action} {device["name"]}')
    
    if device['status'] and house_data['status'] == 'kosong':
        add_notification('danger', f'⚙️ {device["name"]} menyala saat rumah kosong!', 'device')
    
    check_anomalies()
    return jsonify({'device_id': device_id, 'status': device['status']})

@app.route('/api/devices/all/off', methods=['POST'])
def turn_off_all_devices():
    """Matikan semua perangkat"""
    for device_id, device in house_data['devices'].items():
        device['status'] = False
    
    add_log('Kontrol Perangkat', 'Mematikan semua perangkat')
    add_notification('info', '✓ Semua perangkat telah dimatikan')
    
    return jsonify({'message': 'All devices turned off'})

@app.route('/api/notification/clear', methods=['POST'])
def clear_notifications():
    """Hapus semua notifikasi"""
    house_data['notifications'] = []
    return jsonify({'message': 'Notifications cleared'})

if __name__ == '__main__':
    init_mqtt()
    app.run(debug=True, port=5000)
