import requests
from flask import Flask, render_template_string, request, Response
from flask_cors import CORS
from folder_storage_handler import FolderStorageHandler  # Ensure this import is present

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "HEAD", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Range"]
    }
})

# HTML template for the video player
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Video Library</title>
    <link href="https://unpkg.com/video.js/dist/video-js.css" rel="stylesheet">
    <script src="https://unpkg.com/video.js/dist/video.js"></script>
    <script src="https://unpkg.com/@videojs/http-streaming/dist/videojs-http-streaming.js"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #f0f0f0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
        }
        .video-card {
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            overflow: hidden;
            text-align: center;
        }
        .video-thumbnail {
            height: 150px;
            background: #000;
        }
        .video-thumbnail video {
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Library</h1>
        <div class="video-grid">
            {% for video in videos %}
            <div class="video-card" onclick="window.location.href='/play/{{ video.id }}'">
                <div class="video-thumbnail">
                    <video width="100%" height="100%" muted playsinline>
                        <source src="/proxy/{{ video.id }}" type="application/x-mpegURL">
                    </video>
                </div>
                <p>{{ video.name }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content for favicon

class HLSPlayer:
    def __init__(self, storage_handler):
        self.storage = storage_handler

    def scan_videos(self):
        """Fetch available videos from the storage bucket."""
        video_ids = self.storage.list_videos()  # Implement this method in your storage handler
        videos = []
        
        print('Fetched Video IDs:', video_ids)  # Log the fetched video IDs
        
        for video_id in video_ids:
            # Filter out unwanted titles
            if 'iframe' in video_id.lower():
                continue
            m3u8_url = f'https://di-yusrkfqf.leasewebultracdn.com/Example_folder_for_m3u8/{video_id}/stream.m3u8'
            print('Constructed m3u8 URL:', m3u8_url)  # Log the constructed m3u8 URL
            video_info = self.get_video_info(video_id, m3u8_url)
            if video_info:
                videos.append(video_info)
        
        return videos

    def get_video_info(self, video_id, m3u8_url):
        """Retrieve video information for the given video ID and m3u8 URL."""
        # Extract the folder name and file name from the m3u8 URL
        folder_name = m3u8_url.split('/')[-2]  # Get the folder name (e.g., 'maverick')
        file_name = m3u8_url.split('/')[-1].replace('.m3u8', '')  # Get the file name without extension (e.g., 'stream')
        return {
            'id': video_id,
            'name': f'{folder_name.capitalize()} {file_name.capitalize()}',  # e.g., 'Maverick Stream'
            'url': m3u8_url
        }

# Initialize your storage handler
LEASEWEB_PRIVATE_CONFIG = {  # Define your configuration here
    'access_key': 'JWC807Z8QRYRFMPRIKII',  # Updated key to match expected configuration
    'secret_key': 'yF1gJBbjj3yWxpSErILjB6ajR0lni/PJzvitbH96',  # Replace with your actual secret
    'endpoint_url': 'https://nl.object-storage.io',  # Updated key to match expected configuration
    'region': 'nl',
    'bucket_name': 'private-bucket-nl'
}
storage_handler = FolderStorageHandler(LEASEWEB_PRIVATE_CONFIG)  # Replace with your actual config

@app.route('/')
def index():
    player = HLSPlayer(storage_handler)  # Pass your storage handler
    videos = player.scan_videos()  # Fetch videos dynamically
    return render_template_string(HTML_TEMPLATE, videos=videos)

@app.route('/proxy/<path:video_name>')
def proxy_video(video_name):
    """Proxy video requests to avoid CORS issues"""
    cdn_url = f"https://di-yusrkfqf.leasewebultracdn.com/Example_folder_for_m3u8/{video_name}/stream.m3u8"
    response = requests.get(cdn_url)
    return Response(response.content, content_type='application/x-mpegURL')

@app.route('/proxy/key/<path:key_name>')
def proxy_key(key_name):
    """Proxy key requests to avoid CORS issues"""
    key_url = f"https://nl.object-storage.io/private-bucket-nl/Example_folder_for_Key/{key_name}"
    response = requests.get(key_url)
    return Response(response.content, content_type='application/octet-stream')

@app.route('/play/<video_id>')
def play_video(video_id):
    """Render the video player for the selected video."""
    m3u8_url = f'https://di-yusrkfqf.leasewebultracdn.com/Example_folder_for_m3u8/{video_id}/stream.m3u8'
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Player</title>
        <link href="https://unpkg.com/video.js/dist/video-js.css" rel="stylesheet">
        <script src="https://unpkg.com/video.js/dist/video.js"></script>
        <script src="https://unpkg.com/@videojs/http-streaming/dist/videojs-http-streaming.js"></script>
    </head>
    <body>
        <h1>Now Playing: Video {video_id}</h1>
        <video id="video-player" class="video-js" controls preload="auto" width="640" height="264">
            <source src="{{ m3u8_url }}" type="application/x-mpegURL">
        </video>
        <script>
            var player = videojs('video-player');
        </script>
    </body>
    </html>
    ''', video_id=video_id, m3u8_url=m3u8_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 