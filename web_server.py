from flask import Flask, send_from_directory, Response, request
import os
from pathlib import Path
import requests
import urllib.parse
import logging
from config import LEASEWEB_CONFIG
from storage_handler import LeasewebStorageHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize storage handler with error handling
try:
    storage = LeasewebStorageHandler(LEASEWEB_CONFIG)
    # Test connection immediately
    if not storage.check_connection():
        logger.error("Failed to connect to Leaseweb storage. Check your credentials.")
except Exception as e:
    logger.error(f"Error initializing storage handler: {str(e)}")
    storage = None

# Ensure the test_players directory exists
try:
    Path("test_players").mkdir(exist_ok=True)
except Exception as e:
    logger.error(f"Error creating test_players directory: {str(e)}")

@app.route('/health')
def health_check():
    """Health check endpoint"""
    if storage and storage.check_connection():
        return "Healthy", 200
    return "Unhealthy - Storage connection failed", 500

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
        # Log the incoming request
        logger.info(f"Proxy request for: {video_path}")
        
        # Construct the full path in storage
        if video_path.startswith('segments/'):
            # If it's a segment, we need to prepend the video name path
            video_name = request.args.get('video')
            if not video_name:
                # Try to extract video name from referer
                referer = request.headers.get('Referer', '')
                if 'player?video=' in referer:
                    video_name = referer.split('player?video=')[1].split('&')[0]
            
            if video_name:
                storage_path = f"videos/{video_name}/{video_path}"
            else:
                logger.error("Could not determine video name for segment request")
                return "Video name not found", 400
        else:
            storage_path = video_path

        logger.info(f"Accessing storage path: {storage_path}")
        
        # Generate presigned URL
        presigned_url = storage.generate_presigned_url(storage_path)
        
        if not presigned_url:
            logger.error(f"Failed to generate presigned URL for {storage_path}")
            return "File not found", 404

        # Fetch content from storage
        response = requests.get(presigned_url, timeout=30)
        
        if response.status_code == 200:
            content = response.content
            
            # If this is an m3u8 file, modify the URLs
            if video_path.endswith('.m3u8'):
                content = modify_m3u8_urls(content.decode('utf-8'), video_name if 'video_name' in locals() else None)
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
            logger.error(f"Storage returned status {response.status_code} for {storage_path}")
            return f"Storage returned status {response.status_code}", response.status_code
            
    except requests.Timeout:
        logger.error(f"Timeout while fetching: {video_path}")
        return "Gateway Timeout", 504
    except Exception as e:
        logger.error(f"Proxy error for {video_path}: {str(e)}")
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

def modify_m3u8_urls(content, video_name=None):
    """Modify URLs in m3u8 file to use our proxy"""
    lines = content.split('\n')
    modified_lines = []
    
    for line in lines:
        line = line.strip()
        if line.endswith('.ts') or line.endswith('.m3u8') or line.endswith('.key'):
            # Convert the segment path to our proxy URL
            if not line.startswith('http'):
                if video_name and line.startswith('segments/'):
                    # For segment files, add video parameter
                    modified_lines.append(f'/proxy/{line}?video={video_name}')
                else:
                    modified_lines.append(f'/proxy/{line}')
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 