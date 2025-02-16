from flask import Flask, send_from_directory, Response, request
import os
from pathlib import Path
import requests
import urllib.parse
from config import LEASEWEB_CONFIG
from storage_handler import LeasewebStorageHandler

app = Flask(__name__)
storage = LeasewebStorageHandler(LEASEWEB_CONFIG)

# Ensure the test_players directory exists
Path("test_players").mkdir(exist_ok=True)

@app.route('/')
def index():
    """Serve the main page"""
    return """
    <html>
        <head>
            <title>Video Player</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                }
                .form-container {
                    background: #f5f5f5;
                    padding: 20px;
                    border-radius: 8px;
                    margin-top: 20px;
                }
                input, button {
                    padding: 10px;
                    margin: 5px 0;
                }
                button {
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <h1>Video Player</h1>
            <div class="form-container">
                <form action="/player" method="get">
                    <input type="text" name="video" placeholder="Enter video name" required>
                    <button type="submit">Load Video</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.route('/player')
def player():
    """Generate and serve the video player"""
    video_name = request.args.get('video')
    if not video_name:
        return "Video name is required", 400

    from test_player import VideoPlayerTester
    tester = VideoPlayerTester(storage)
    player_file = tester.generate_test_player(video_name)
    
    return send_from_directory('test_players', f'{video_name}_player.html')

@app.route('/proxy/<path:video_path>')
def proxy(video_path):
    """Proxy requests to Leaseweb storage"""
    try:
        # Generate presigned URL
        presigned_url = storage.generate_presigned_url(video_path)
        
        if not presigned_url:
            return "File not found", 404

        # Fetch content from storage
        response = requests.get(presigned_url, timeout=30)
        
        if response.status_code == 200:
            content = response.content
            
            # If this is an m3u8 file, modify the URLs
            if video_path.endswith('.m3u8'):
                content = modify_m3u8_urls(content.decode('utf-8'))
                content = content.encode('utf-8')
            
            # Determine content type
            content_type = get_content_type(video_path)
            
            # Create response with proper headers
            resp = Response(content)
            resp.headers['Content-Type'] = content_type
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Cache-Control'] = 'public, max-age=3600'
            
            return resp
        else:
            return f"Storage returned status {response.status_code}", response.status_code
            
    except requests.Timeout:
        return "Gateway Timeout", 504
    except Exception as e:
        return f"Server Error: {str(e)}", 500

def get_content_type(path):
    """Determine content type based on file extension"""
    if path.endswith('.m3u8'):
        return 'application/vnd.apple.mpegurl'
    elif path.endswith('.ts'):
        return 'video/mp2t'
    elif path.endswith('.key'):
        return 'application/octet-stream'
    else:
        return 'application/octet-stream'

def modify_m3u8_urls(content):
    """Modify URLs in m3u8 file to use our proxy"""
    lines = content.split('\n')
    modified_lines = []
    
    for line in lines:
        line = line.strip()
        if line.endswith('.ts') or line.endswith('.m3u8') or line.endswith('.key'):
            # Convert the segment path to our proxy URL
            if not line.startswith('http'):
                modified_lines.append(f'/proxy/{line}')
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 