import os
import re
import urllib.parse
import requests
from flask import Flask, render_template, request, jsonify, abort

app = Flask(__name__)

# External API Root URL
BASE_API_URL = "https://private-message-room-api.vercel.app/"

# Browser Headers (Bypassing protection)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def parse_html_messages(html_text):
    """Parses Name, Message, and Date from HTML and safely URL-decodes them"""
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    pattern = r'Name:\s*(.*?)\s*Message:\s*(.*?)\s*Date:\s*(.*?)(?=\s*Name:|\s*#|\Z)'
    matches = re.findall(pattern, clean_text, re.IGNORECASE)
    
    messages = []
    for match in matches:
        name = match[0].strip()
        msg_val = match[1].strip()
        date_val = match[2].strip()
        
        msg_val = msg_val.strip('\'"“”‘’')
        
        name_decoded = urllib.parse.unquote(name)
        msg_decoded = urllib.parse.unquote(msg_val)
        
        if name_decoded or msg_decoded:
            messages.append({
                "name": name_decoded,
                "message": msg_decoded,
                "date": date_val
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
            return jsonify({
                "success": True, 
                "messages": messages, 
                "source": "external"
            })
        else:
            return jsonify({
                "success": False, 
                "error": f"API Status: {response.status_code}"
            })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Connection Error: {str(e)[:60]}"
        })

@app.route('/api/messages', methods=['POST'])
def send_message():
    try:
        data = request.json or {}
        name = data.get('name', 'Anonymous').strip()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({"success": False, "error": "Message content empty"}), 400

        # Encode URLs to Hex to bypass Vercel's path routing blocks
        if message.startswith("https://") or message.startswith("http://"):
            message = "HEX_" + message.encode('utf-8').hex()

        name_encoded = urllib.parse.quote(name)
        message_encoded = urllib.parse.quote(message)
        
        send_url = f"{BASE_API_URL}{name_encoded}/{message_encoded}"

        response = requests.get(send_url, headers=HEADERS, timeout=10)
        if response.status_code in [200, 201]:
            return jsonify({"success": True})
        else:
            return jsonify({
                "success": False, 
                "error": f"API SEND Status: {response.status_code}"
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Safe 10MB upload (Forward to tmpfiles.org for robust serverless hosting)
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400
        
    # Check Content-Length (10MB limit)
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify({"success": False, "error": "File exceeds the 10MB limit"}), 400
        
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'mp3', 'wav', 'webm', 'ogg', 'm4a'}
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": "Invalid format. Only images and standard audio allowed."}), 400

    # Forward the file to tmpfiles.org (Auto-deletes in 1 hour)
    try:
        files = {
            'file': (file.filename, file.read(), file.mimetype or 'application/octet-stream')
        }
        response = requests.post(
            'https://tmpfiles.org/api/v1/upload', 
            files=files,
            timeout=15
        )
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("status") == "success":
                raw_url = res_data["data"]["url"]
                # Convert page URL to direct download URL
                direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                return jsonify({
                    "success": True, 
                    "url": direct_url
                })
        
        return jsonify({
            "success": False, 
            "error": f"Upload service failed with status code {response.status_code}"
        }), 502
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Upload failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)