"""
app.py
Flask + Flask-SocketIO 主服务
访问: http://<树莓派IP>:5000
"""
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit

from spectrometer import SpectrometerController
from storage import save_csv, save_hdf5, list_saved_files, SAVE_DIR
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'usb2000-secret'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

ctrl = SpectrometerController()

# ─── 实时采集状态 ────────────────────────────────────────────
_streaming = False
_stream_interval = 0.2   # 秒
_scans_to_average = 1


def _stream_loop():
    while _streaming:
        try:
            wl, inten = ctrl.get_spectrum(_scans_to_average)
            socketio.emit('spectrum_data', {
                'wavelengths': wl,
                'intensities': inten,
            })
        except Exception as e:
            socketio.emit('error', {'msg': str(e)})
        time.sleep(_stream_interval)


# ─── HTTP 路由 ────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/connect', methods=['POST'])
def api_connect():
    mock = request.json.get('mock', False) if request.is_json else False
    try:
        model = ctrl.connect(mock=mock)
        return jsonify({'status': 'ok', 'model': model})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(ctrl.get_status())


@app.route('/api/integration_time', methods=['POST'])
def api_integration_time():
    ms = float(request.json['ms'])
    actual_ms = ctrl.set_integration_time(ms)
    return jsonify({'status': 'ok', 'actual_ms': actual_ms})


@app.route('/api/scans_average', methods=['POST'])
def api_scans_average():
    global _scans_to_average
    _scans_to_average = max(1, int(request.json.get('count', 1)))
    return jsonify({'status': 'ok', 'count': _scans_to_average})


@app.route('/api/dark', methods=['POST'])
def api_dark():
    try:
        scans = int(request.json.get('scans', 3)) if request.is_json else 3
        msg = ctrl.capture_dark(scans)
        return jsonify({'status': 'ok', 'msg': msg})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/api/reference', methods=['POST'])
def api_reference():
    try:
        scans = int(request.json.get('scans', 3)) if request.is_json else 3
        msg = ctrl.capture_reference(scans)
        return jsonify({'status': 'ok', 'msg': msg})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/api/spectrum', methods=['GET'])
def api_spectrum():
    try:
        wl, inten = ctrl.get_spectrum(_scans_to_average)
        return jsonify({'wavelengths': wl, 'intensities': inten})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/api/reflectance', methods=['GET'])
def api_reflectance():
    try:
        wl, ref = ctrl.get_reflectance(_scans_to_average)
        return jsonify({'wavelengths': wl, 'reflectance': ref})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 400


@app.route('/api/save', methods=['POST'])
def api_save():
    data_type = request.json.get('type', 'spectrum')
    fmt  = request.json.get('format', 'csv')
    note = request.json.get('note', '')
    try:
        if data_type == 'reflectance':
            wl, data = ctrl.get_reflectance(_scans_to_average)
            label = 'reflectance_pct'
        else:
            wl, data = ctrl.get_spectrum(_scans_to_average)
            label = 'intensity_counts'

        if fmt == 'hdf5':
            path = save_hdf5(wl, data, label, note)
        else:
            path = save_csv(wl, data, label, note)

        return jsonify({'status': 'ok', 'path': path,
                        'filename': os.path.basename(path)})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/api/files', methods=['GET'])
def api_files():
    return jsonify(list_saved_files())


@app.route('/api/download/<filename>')
def api_download(filename):
    path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': '文件不存在'}), 404
    return send_file(path, as_attachment=True)


# ─── WebSocket 事件 ───────────────────────────────────────────

@socketio.on('start_stream')
def ws_start_stream(data):
    global _streaming, _stream_interval
    interval = float(data.get('interval', 0.2)) if data else 0.2
    _stream_interval = max(0.05, interval)
    _streaming = True
    t = threading.Thread(target=_stream_loop, daemon=True)
    t.start()
    emit('stream_status', {'streaming': True})


@socketio.on('stop_stream')
def ws_stop_stream():
    global _streaming
    _streaming = False
    emit('stream_status', {'streaming': False})


if __name__ == '__main__':
    print('=' * 50)
    print(' 海洋光学 USB2000+ 光谱仪控制台')
    print(' 访问地址: http://0.0.0.0:5000')
    print(' 局域网:   http://<树莓派IP>:5000')
    print('=' * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
