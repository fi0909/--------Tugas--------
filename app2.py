from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json

app = Flask(__name__)

# State Management
state = {
    'occupied': False,
    'rooms': {
        'kamar1': {'light': False, 'occupancy': False},
        'kamar2': {'light': False, 'occupancy': False},
        'kamar3': {'light': False, 'occupancy': False},
        'ruang_keluarga': {'light': False, 'occupancy': False},
        'dapur': {'light': False, 'occupancy': False},
        'ruang_cuci_baju': {'light': False, 'occupancy': False},
        'kamar_mandi': {'light': False, 'occupancy': False},
        'teras_garasi': {'light': False, 'occupancy': False},
    },
    'devices': {
        'mesin_cuci': {'status': False, 'power': 500},
        'pompa_air': {'status': False, 'power': 200},
        'kompor': {'status': False, 'power': 300},
    },
    'energy_usage': 0,
    'peak_usage': 0,
    'avg_usage': 0,
    'logs': [],
    'notifications': []
}

def calculate_energy():
    """Calculate total energy usage"""
    total = 0
    
    # Setiap lampu menggunakan 50W
    for room_id, room_data in state['rooms'].items():
        if room_data['light']:
            total += 50
    
    # Device power
    for device_id, device_data in state['devices'].items():
        if device_data['status']:
            total += device_data['power']
    
    state['energy_usage'] = total
    if total > state['peak_usage']:
        state['peak_usage'] = total
    
    # Calculate average (simplified)
    state['avg_usage'] = (state['avg_usage'] + total) / 2

def add_log(action, detail):
    """Add activity log"""
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S")
    
    log_entry = {
        'timestamp': timestamp,
        'action': action,
        'detail': detail
    }
    
    state['logs'].append(log_entry)
    
    # Keep only last 50 logs
    if len(state['logs']) > 50:
        state['logs'] = state['logs'][-50:]

def check_anomalies():
    """Check for anomalies and add notifications"""
    state['notifications'] = []
    
    # Check for lights on when house is empty
    if not state['occupied']:
        for room_id, room_data in state['rooms'].items():
            if room_data['light']:
                state['notifications'].append({
                    'type': 'warning',
                    'icon': '💡',
                    'message': f'Lampu di {get_room_name(room_id)} masih nyala padahal rumah kosong!'
                })
    
    # Check for devices on when house is empty
    if not state['occupied']:
        for device_id, device_data in state['devices'].items():
            if device_data['status']:
                state['notifications'].append({
                    'type': 'danger',
                    'icon': '⚙️',
                    'message': f'{get_device_name(device_id)} masih aktif padahal rumah kosong!'
                })
    
    # Check for high energy usage
    if state['energy_usage'] > 3200:  # 80% of 4000W
        state['notifications'].append({
            'type': 'warning',
            'icon': '⚡',
            'message': f'Penggunaan listrik tinggi: {round(state["energy_usage"])}W'
        })

def get_room_name(room_id):
    """Get room display name"""
    room_names = {
        'kamar1': 'Kamar 1',
        'kamar2': 'Kamar 2',
        'kamar3': 'Kamar 3',
        'ruang_keluarga': 'Ruang Keluarga',
        'dapur': 'Dapur',
        'ruang_cuci_baju': 'Ruang Cuci Baju',
        'kamar_mandi': 'Kamar Mandi',
        'teras_garasi': 'Teras/Garasi',
    }
    return room_names.get(room_id, room_id)

def get_device_name(device_id):
    """Get device display name"""
    device_names = {
        'mesin_cuci': 'Mesin Cuci',
        'pompa_air': 'Pompa Air',
        'kompor': 'Kompor',
    }
    return device_names.get(device_id, device_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current status"""
    calculate_energy()
    check_anomalies()
    
    return jsonify({
        'success': True,
        'status': {
            'occupied': state['occupied'],
            'rooms': state['rooms'],
            'devices': state['devices'],
            'energy_usage': state['energy_usage'],
            'peak_usage': state['peak_usage'],
            'avg_usage': state['avg_usage'],
        },
        'notifications': state['notifications'],
        'logs': state['logs']
    })

@app.route('/api/set-house-mode/<mode>', methods=['POST'])
def set_house_mode(mode):
    """Set house mode (occupied/empty)"""
    occupied = mode == 'occupied'
    state['occupied'] = occupied
    
    action = 'Mode rumah diubah'
    detail = 'Ditempati' if occupied else 'Kosong'
    add_log(action, detail)
    
    return jsonify({
        'success': True,
        'occupied': occupied
    })

@app.route('/api/toggle-light/<room_id>', methods=['POST'])
def toggle_light(room_id):
    """Toggle light in a room"""
    if room_id not in state['rooms']:
        return jsonify({'success': False, 'error': 'Ruangan tidak ditemukan'}), 404
    
    room = state['rooms'][room_id]
    
    # Check if room is occupied
    if room['occupancy'] and not room['light']:
        return jsonify({'success': False, 'error': 'Tidak bisa menyalakan lampu saat ruangan terisi'}), 400
    
    room['light'] = not room['light']
    
    action = f"Lampu {get_room_name(room_id)}"
    detail = 'Dinyalakan' if room['light'] else 'Dimatikan'
    add_log(action, detail)
    
    calculate_energy()
    check_anomalies()
    
    return jsonify({'success': True})

@app.route('/api/toggle-all-lights', methods=['POST'])
def toggle_all_lights():
    """Turn off all lights"""
    if state['occupied']:
        return jsonify({'success': False, 'error': 'Tidak bisa mematikan semua lampu saat rumah terisi'}), 400
    
    # Turn off all lights
    for room_id, room_data in state['rooms'].items():
        if room_data['light']:
            room_data['light'] = False
    
    add_log('Semua lampu', 'Dimatikan sekaligus')
    calculate_energy()
    check_anomalies()
    
    return jsonify({'success': True})

@app.route('/api/set-occupancy/<room_id>/<status>', methods=['POST'])
def set_occupancy(room_id, status):
    """Set room occupancy"""
    if room_id not in state['rooms']:
        return jsonify({'success': False, 'error': 'Ruangan tidak ditemukan'}), 404
    
    occupied = status.lower() == 'true'
    state['rooms'][room_id]['occupancy'] = occupied
    
    action = f"{get_room_name(room_id)}"
    detail = 'Terisi' if occupied else 'Kosong'
    add_log(action, detail)
    
    check_anomalies()
    
    return jsonify({'success': True})

@app.route('/api/toggle-device/<device_id>', methods=['POST'])
def toggle_device(device_id):
    """Toggle device"""
    if device_id not in state['devices']:
        return jsonify({'success': False, 'error': 'Perangkat tidak ditemukan'}), 404
    
    device = state['devices'][device_id]
    
    # Check if any room is occupied
    any_occupied = any(room['occupancy'] for room in state['rooms'].values())
    if any_occupied and not device['status']:
        return jsonify({'success': False, 'error': 'Tidak bisa menyalakan perangkat saat ada penghuni'}), 400
    
    device['status'] = not device['status']
    
    action = get_device_name(device_id)
    detail = 'Diaktifkan' if device['status'] else 'Dimatikan'
    add_log(action, detail)
    
    calculate_energy()
    check_anomalies()
    
    return jsonify({'success': True})

@app.route('/api/toggle-all-devices', methods=['POST'])
def toggle_all_devices():
    """Turn off all devices"""
    if state['occupied']:
        return jsonify({'success': False, 'error': 'Tidak bisa mematikan semua perangkat saat rumah terisi'}), 400
    
    # Turn off all devices
    for device_id, device_data in state['devices'].items():
        if device_data['status']:
            device_data['status'] = False
    
    add_log('Semua perangkat', 'Dimatikan sekaligus')
    calculate_energy()
    check_anomalies()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
