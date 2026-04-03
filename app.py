import csv
import json
import os
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

CSV_FILE = 'gamestate.csv'
LOCK = threading.Lock()

# ── CSV layout ──────────────────────────────────────────────────────────────
# One row, one column called "data" that holds the full JSON blob.
# Simple and gives us a plain-text audit trail you can open in Excel.

def _default_state():
    return {
        "regions": {
            "east":  {"runs": 0, "bases": [None, None, None], "plays": []},
            "south": {"runs": 0, "bases": [None, None, None], "plays": []},
            "west":  {"runs": 0, "bases": [None, None, None], "plays": []}
        },
        "repStats": {},
        "lastUpdated": ""
    }

def read_state():
    """Read game state from CSV. Returns default state if file missing/empty."""
    with LOCK:
        if not os.path.exists(CSV_FILE):
            return _default_state()
        try:
            with open(CSV_FILE, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    return json.loads(row['data'])
        except Exception:
            pass
        return _default_state()

def write_state(state: dict):
    """Write game state to CSV as a single JSON blob."""
    state['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
    with LOCK:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'data'])
            writer.writeheader()
            writer.writerow({
                'timestamp': state['lastUpdated'],
                'data': json.dumps(state)
            })

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the frontend HTML."""
    return app.send_static_file('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    """Return full game state as JSON."""
    return jsonify(read_state())

@app.route('/api/state', methods=['POST'])
def set_state():
    """Replace full game state from JSON body."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        write_state(data)
        return jsonify({'ok': True, 'lastUpdated': data.get('lastUpdated', '')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_state():
    """Wipe game state back to defaults."""
    state = _default_state()
    write_state(state)
    return jsonify({'ok': True})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
