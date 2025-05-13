from flask import Flask, request, jsonify
import time
import miniupnpc

app = Flask(__name__)
swarms = {}  # {chat_id: {peer_id: (ip, port, pubkey, last_seen)}}
messages = {}  # {peer_id: [ {from, text, timestamp} ] }
TIMEOUT = 60
users = set()  # Множина зареєстрованих username

def upnp_forward_port(port):
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        upnp.addportmapping(port, 'TCP', upnp.lanaddr, port, 'Tracker Server', '')
        print(f"[UPNP] Port {port} forwarded on router!")
    except Exception as e:
        print(f"[UPNP] Port forwarding failed: {e}")

@app.route('/announce', methods=['POST'])
def announce():
    data = request.json
    chat_id = data['chat_id']
    peer_id = data['peer_id']
    ip = data.get('ip', '')
    port = data.get('port', '')
    pubkey = data.get('pubkey', '')
    now = time.time()
    if chat_id not in swarms:
        swarms[chat_id] = {}
    swarms[chat_id][peer_id] = (ip, port, pubkey, now)
    return jsonify({'status': 'ok'})

@app.route('/get_peers')
def get_peers():
    chat_id = request.args['chat_id']
    now = time.time()
    peers = []
    if chat_id in swarms:
        # Remove old peers
        swarms[chat_id] = {pid: (ip, port, pubkey, t) for pid, (ip, port, pubkey, t) in swarms[chat_id].items() if now - t < TIMEOUT}
        for pid, (ip, port, pubkey, t) in swarms[chat_id].items():
            peers.append({'peer_id': pid, 'ip': ip, 'port': port, 'pubkey': pubkey})
    return jsonify({'peers': peers})

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    to_peer = data['to_peer']
    from_peer = data['from_peer']
    text = data['text']
    timestamp = time.time()
    if to_peer not in messages:
        messages[to_peer] = []
    messages[to_peer].append({'from': from_peer, 'text': text, 'timestamp': timestamp})
    return jsonify({'status': 'ok'})

@app.route('/get_messages')
def get_messages():
    peer_id = request.args['peer_id']
    msgs = messages.get(peer_id, [])
    messages[peer_id] = []  # clear after fetch
    return jsonify({'messages': msgs})

@app.route('/public_trackers')
def public_trackers():
    # Тут можна додати реальні публічні трекери
    trackers = [
        {'url': 'http://127.0.0.1:9000', 'description': 'Local test tracker'}
    ]
    return jsonify({'trackers': trackers})

@app.route('/send_private_message', methods=['POST'])
def send_private_message():
    data = request.json
    to_user = data['to_user']
    from_peer = data['from_peer']
    text = data['text']
    timestamp = time.time()
    if to_user not in messages:
        messages[to_user] = []
    messages[to_user].append({'from': from_peer, 'text': text, 'timestamp': timestamp})
    return jsonify({'status': 'ok'})

@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.json
    username = data['username']
    users.add(username)
    return jsonify({'status': 'ok'})

@app.route('/get_private_messages')
def get_private_messages():
    username = request.args['user']
    msgs = messages.get(username, [])
    messages[username] = []  # очищаємо після видачі
    return jsonify({'messages': msgs})

if __name__ == '__main__':
    try:
        upnp_forward_port(9000)
    except ImportError:
        print("[WARN] miniupnpc not installed, UPnP port forwarding skipped.")
    app.run(host='0.0.0.0', port=9000) 