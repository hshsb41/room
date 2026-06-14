import os
import re
import urllib.parse
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# External API Configuration
BASE_API_URL = "https://private-message-room-api.vercel.app/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_html_messages(html_text):
    """HTML bata Name, Message, ra Date extract garne function"""
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Message pattern match garne regex
    pattern = r'Name:\s*(.*?)\s*Message:\s*(.*?)\s*Date:\s*(.*?)(?=\s*Name:|\s*#|\Z)'
    matches = re.findall(pattern, clean_text, re.IGNORECASE)
    
    messages = []
    for match in matches:
        name_decoded = urllib.parse.unquote(match[0].strip())
        msg_val = match[1].strip().strip('\'"“”‘’')
        msg_decoded = urllib.parse.unquote(msg_val)
        
        if name_decoded or msg_decoded:
            messages.append({
                "name": name_decoded,
                "message": msg_decoded,
                "date": match[2].strip()
            })
            
    return messages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/messages', methods=['GET'])
def get_messages():
    try:
        response = requests.get(BASE_API_URL, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            messages = parse_html_messages(response.text)
            return jsonify({"success": True, "messages": messages})
        else:
            return jsonify({"success": False, "error": "API Error"})
    except Exception as e:
        return jsonify({"success": False, "error": "Connection Failed"})

@app.route('/api/messages', methods=['POST'])
def send_message():
    try:
        data = request.json or {}
        name = data.get('name', 'Anonymous').strip()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({"success": False, "error": "Empty Message"}), 400

        # Link haru pathauda HEX encoding garne (Bypass Vercel block)
        if message.startswith("http"):
            message = "HEX_" + message.encode('utf-8').hex()

        name_encoded = urllib.parse.quote(name)
        message_encoded = urllib.parse.quote(message)
        
        send_url = f"{BASE_API_URL}{name_encoded}/{message_encoded}"

        response = requests.get(send_url, headers=HEADERS, timeout=10)
        if response.status_code in [200, 201]:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Send Failed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Catbox.moe ma file upload garne function (Sajilo ra Stable)"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400
        
    file = request.files['file']
    
    try:
        # Catbox API lai chahine data
        files = {'fileToUpload': (file.filename, file.read())}
        payload = {'reqtype': 'fileupload', 'userhash': ''}
        
        response = requests.post('https://catbox.moe/user/api.php', files=files, data=payload, timeout=20)
        
        if response.status_code == 200:
            file_url = response.text.strip() # Direct URL pathauchha
            return jsonify({
                "success": True, 
                "url": file_url
            })
        else:
            return jsonify({"success": False, "error": "Upload Service Down"}), 502
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)