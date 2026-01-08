from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json
import os
import paho.mqtt.client as mqtt 

BROKER = '192.168.0.100'
PORT = 1883
app = Flask(__name__)

# Data storage (dalam production gunakan database)
house_data = {
    'status': 'kosong',  # kosong or berpenghuni
    'mqtt_connected': False,
    'rooms': {
        'kamar1': {'name': 'Kamar 1', 'light': False, 'occupied': False},
        'kamar2': {'name': 'Kamar 2', 'light': False, 'occupied': False},
        'kamar3': {'name': 'Kamar 3', 'light': False, 'occupied': False},
        'dapur': {'name': 'Dapur', 'light': False, 'occupied': False},
        'ruang_cuci': {'name': 'Ruang Cuci Baju', 'light': False, 'occupied': False},
    },
    'devices': {
        'mesinCuci': {'name': 'Mesin Cuci', 'status': False, 'icon': '🔄'},
        'pompa_air': {'name': 'Pompa Air', 'status': False, 'icon': '💧'},
        'kompor': {'name': 'Kompor', 'status': False, 'icon': '🔥'},
        'kulkas': {'name': 'Kulkas', 'status': False, 'icon': '❄️'},
    },
    'notifications': [],
    'logs': [],
    'notification_sound_active': None  # Track which sound is playing
}

rooms = list(house_data['rooms'].keys())
index_ruangcuci = rooms.index('ruang_cuci')
rooms[index_ruangcuci] = 'jemuran'
devices = list(house_data['devices'].keys())
devices.append('lampu')  # Tambah lampu sebagai device untuk monitoring
lock_topic = "smarthome/lock"
presence = {room: 0 for room in rooms}
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        house_data['mqtt_connected'] = True
        print("Connected with result code", rc)

        # Subscribe PIR
        for room in rooms:
            client.subscribe(f"smarthome/deteksi/{room}")

        # Subscribe monitoring device
        for room in rooms:
            for dev in devices:
                if dev == 'pompa_air':
                    dev = 'pompa'
                client.subscribe(f"smarthome/{room}/{dev}")
        add_log('MQTT', 'Terhubung ke broker MQTT')
    else:
        print("Failed to connect, return code %d\n", rc)
        house_data['mqtt_connected'] = False

    print("Subscribed to all topics!")
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    # Handle PIR
    for room in rooms:
        if topic == f"smarthome/deteksi/{room}":
            presence[room] = int(payload)
            update_global_lock(client)
            if any(presence.values()):
                house_data['status'] = 'berpenghuni'
            else:
                house_data['status'] = 'kosong'
            if room == 'jemuran':
                room = 'ruang_cuci'
                house_data['rooms'][room]['occupied'] = int(payload)
            else:
                house_data['rooms'][room]['occupied'] = int(payload)
            return
    for room in rooms:
        for dev in devices:
            if dev == 'pompa_air':
                dev = 'pompa'
            if topic == f"smarthome/{room}/{dev}":
                if dev == 'lampu':
                    light_status = 1 if payload == 'lampu/nyala' else 0
                    if room == 'jemuran':
                        room = 'ruang_cuci'
                        house_data['rooms'][room]['light'] = light_status
                    else:
                        house_data['rooms'][room]['light'] = light_status
                else:
                    dev_status = 1 if payload == f'{dev}/nyala' else 0
                    dev = 'pompa_air' if dev == 'pompa' else dev
                    house_data['devices'][dev]['status'] = dev_status
                return
    
def update_global_lock(client):
    if any(presence.values()):
        client.publish(lock_topic, "1")
        print("⚠ LOCK AKTIF (Ada orang!)")
    else:
        client.publish(lock_topic, "0")
        print("✔ LOCK NON-AKTIF (Rumah kosong)")

def send_command(client, room, device, state):
    if room not in rooms:
        print(f"Ruangan '{room}' tidak dikenali!")
        return

    if device not in devices:
        print(f"Device '{device}' tidak dikenali!")
        return

    if state not in ["on", "off"]:
        print("Gunakan 'on' atau 'off'")
        return

    val = "1" if state == "on" else "0"
    if device == 'pompa_air':
        device = 'pompa'
        topic = f"smarthome/{room}/{device}/perintah"
    else:
        topic = f"smarthome/{room}/{devices[devices.index(device)]}/perintah"

    print(f"Mengirim ke [{topic}] → {val}")
    client.publish(topic, val)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()
def add_log(action, details):
    """Tambah log aktivitas"""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
        'details': details
    }
    house_data['logs'].append(log_entry)
    if len(house_data['logs']) > 100:  # Keep only last 100 logs
        house_data['logs'] = house_data['logs'][-100:]

def check_anomalies():
    """Check for anomalies and add notifications"""
    house_data['notifications'] = []
    
    # Check for lights on when house is empty
    if not house_data['status'] == 'berpenghuni':
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
    if not house_data['status'] == 'berpenghuni':
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
        'type': type,  # warning, info, danger
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
    
    # Jika ada penghuni, tidak bisa toggle off hanya bisa toggle on
    if house_data['status'] == 'berpenghuni' and current_state:
        add_notification('warning', f'Lampu {room["name"]} tidak bisa dimatikan saat ada penghuni')
        return jsonify({'error': 'Cannot turn off lights when occupied'}), 403
    
    room['light'] = not current_state
    
    action = 'Menyalakan' if room['light'] else 'Mematikan'
    add_log('Kontrol Lampu', f'{action} lampu {room["name"]}')
    if room_id == 'ruang_cuci':
        send_command(client, "jemuran", 'lampu', 'on' if room['light'] else 'off')
    else:
        send_command(client, room_id, 'lampu', 'on' if room['light'] else 'off')


    # Notifikasi jika lampu menyala saat rumah kosong
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
        if room_id == 'ruang_cuci':
            send_command(client, "jemuran", 'lampu', 'on' if room['light'] else 'off')
        else:
            send_command(client, room_id, 'lampu', 'on' if room['light'] else 'off')

    
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
    if device_id == 'kulkas' or device_id == 'kompor':
        send_command(client, 'dapur', device_id, 'on' if device['status'] else 'off')
    if device_id == 'mesinCuci' or device_id == 'pompa_air':
        send_command(client, 'jemuran', device_id, 'on' if device['status'] else 'off')
    
    if device['status'] and house_data['status'] == 'kosong':
        add_notification('danger', f'⚙️ {device["name"]} menyala saat rumah kosong!', 'device')
    
    check_anomalies()
    return jsonify({'device_id': device_id, 'status': device['status']})

@app.route('/api/devices/all/off', methods=['POST'])
def turn_off_all_devices():
    """Matikan semua perangkat"""
    for device_id, device in house_data['devices'].items():
        device['status'] = False
        if device_id == 'kulkas' or device_id == 'kompor':
            send_command(client, 'dapur', device_id, 'on' if device['status'] else 'off')
        if device_id == 'mesinCuci' or device_id == 'pompa_air':
            send_command(client, 'jemuran', device_id, 'on' if device['status'] else 'off')
    
    add_log('Kontrol Perangkat', 'Mematikan semua perangkat')
    add_notification('info', '✓ Semua perangkat telah dimatikan')
    
    return jsonify({'message': 'All devices turned off'})

@app.route('/api/house/status', methods=['POST'])
def set_house_status():
    """Set status rumah (kosong/berpenghuni)"""
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['kosong', 'berpenghuni']:
        return jsonify({'error': 'Invalid status'}), 400
    
    old_status = house_data['status']
    house_data['status'] = new_status
    
    add_log('Status Rumah', f'Status berubah dari {old_status} menjadi {new_status}')
    add_notification('info', f'Status rumah: {new_status}')
    
    check_anomalies()
    return jsonify({'status': new_status})

@app.route('/api/notification/clear', methods=['POST'])
def clear_notifications():
    """Hapus semua notifikasi"""
    house_data['notifications'] = []
    return jsonify({'message': 'Notifications cleared'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
