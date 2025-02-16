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
    """Serve the main page with video cards"""
    try:
        # Get list of videos from storage
        videos = list_videos_from_storage()
        
        # Generate HTML for video cards
        video_cards_html = generate_video_cards(videos)
        
        return f"""
        <html>
            <head>
                <title>Video Library</title>
                <script>
                    // URL encoding polyfill
                    if (!window.encodeURIComponent) {{
                        window.encodeURIComponent = function(str) {{
                            return encodeURI(str).replace(/[!'()*]/g, function(c) {{
                                return '%' + c.charCodeAt(0).toString(16);
                            }});
                        }};
                    }}
                </script>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: #f0f0f0;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    h1 {{
                        color: #333;
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .video-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                        gap: 20px;
                        padding: 20px;
                    }}
                    .video-card {{
                        background: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        transition: transform 0.2s;
                        cursor: pointer;
                    }}
                    .video-card:hover {{
                        transform: translateY(-5px);
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    }}
                    .video-thumbnail {{
                        width: 100%;
                        height: 180px;
                        background: #ddd;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: #666;
                    }}
                    .video-info {{
                        padding: 15px;
                    }}
                    .video-title {{
                        margin: 0;
                        font-size: 18px;
                        color: #333;
                    }}
                    .video-meta {{
                        margin-top: 8px;
                        font-size: 14px;
                        color: #666;
                    }}
                    .search-bar {{
                        margin-bottom: 20px;
                        text-align: center;
                    }}
                    .search-bar input {{
                        padding: 10px;
                        width: 300px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        margin-right: 10px;
                    }}
                    .no-videos {{
                        text-align: center;
                        padding: 40px;
                        color: #666;
                        font-size: 18px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Video Library</h1>
                    <div class="search-bar">
                        <input type="text" id="searchInput" placeholder="Search videos..." oninput="filterVideos()">
                    </div>
                    <div class="video-grid" id="videoGrid">
                        {video_cards_html}
                    </div>
                </div>
                
                <script>
                    function filterVideos() {{
                        const searchInput = document.getElementById('searchInput');
                        const filter = searchInput.value.toLowerCase();
                        const cards = document.getElementsByClassName('video-card');
                        
                        for (let card of cards) {{
                            const title = card.getElementsByClassName('video-title')[0].textContent.toLowerCase();
                            if (title.includes(filter)) {{
                                card.style.display = '';
                            }} else {{
                                card.style.display = 'none';
                            }}
                        }}
                    }}
                    
                    function playVideo(videoName) {{
                        window.location.href = '/player?video=' + encodeURIComponent(videoName);
                    }}
                </script>
            </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error generating index page: {str(e)}")
        return f"""
        <html>
            <body>
                <h1>Error</h1>
                <p>Failed to load video library. Please try again later.</p>
                <p>Error: {str(e)}</p>
            </body>
        </html>
        """

def list_videos_from_storage():
    """Get list of videos from storage"""
    try:
        # List objects in the videos directory
        response = storage.session.list_objects(
            Bucket=storage.bucket,
            Prefix='videos/',
            Delimiter='/'
        )
        
        videos = []
        # Extract video names from CommonPrefixes
        for prefix in response.get('CommonPrefixes', []):
            video_name = prefix.get('Prefix', '').split('/')[1]
            if video_name:
                videos.append({
                    'name': video_name,
                    'title': video_name.replace('_', ' ').title(),
                    # You could add more metadata here in the future
                    'duration': 'Unknown',  # Could be fetched from video metadata
                    'date': 'Unknown'  # Could be fetched from storage metadata
                })
        
        return videos
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        return []

def generate_video_cards(videos):
    """Generate HTML for video cards"""
    if not videos:
        return '<div class="no-videos">No videos found</div>'
    
    cards_html = []
    for video in videos:
        card = f"""
        <div class="video-card" onclick="playVideo('{video['name']}')">
            <div class="video-thumbnail">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="#666">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>
            <div class="video-info">
                <h3 class="video-title">{video['title']}</h3>
                <div class="video-meta">
                    <div>Duration: {video['duration']}</div>
                    <div>Added: {video['date']}</div>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)
    
    return '\n'.join(cards_html)

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
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Construct the full path in storage
        storage_path = video_path
        video_name = None
        
        # Try to get video name from query parameter
        video_name = request.args.get('video')
        
        # If no video name in query, try to get from referer
        if not video_name:
            referer = request.headers.get('Referer', '')
            logger.info(f"Referer: {referer}")
            if 'player?video=' in referer:
                video_name = urllib.parse.unquote(referer.split('player?video=')[1].split('&')[0])
                logger.info(f"Extracted video name from referer: {video_name}")
        
        # If we have a video name and this is a segment request, construct the full path
        if video_name:
            if 'segments/' in video_path or video_path.endswith('.ts'):
                storage_path = f"videos/{video_name}/{video_path}"
            elif not video_path.startswith('videos/'):
                storage_path = f"videos/{video_name}/{video_path}"
        
        logger.info(f"Final storage path: {storage_path}")
        
        # Generate presigned URL
        presigned_url = storage.generate_presigned_url(storage_path)
        
        if not presigned_url:
            logger.error(f"Failed to generate presigned URL for {storage_path}")
            return "File not found", 404

        # Fetch content from storage
        response = requests.get(presigned_url, timeout=30)
        logger.info(f"Storage response status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content
            
            # If this is an m3u8 file, modify the URLs
            if video_path.endswith('.m3u8'):
                content = modify_m3u8_urls(content.decode('utf-8'), video_name)
                content = content.encode('utf-8')
                logger.info(f"Modified m3u8 content for {video_name}")
            
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

def modify_m3u8_urls(content, video_name):
    """Modify URLs in m3u8 file to use our proxy"""
    lines = content.split('\n')
    modified_lines = []
    
    for line in lines:
        line = line.strip()
        if line.endswith('.ts') or line.endswith('.m3u8') or line.endswith('.key'):
            # Convert the segment path to our proxy URL
            if not line.startswith('http'):
                modified_lines.append(f'/proxy/{line}?video={video_name}')
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 