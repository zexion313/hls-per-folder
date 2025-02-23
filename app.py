from flask import Flask, Response, request, send_from_directory
import requests
import urllib.parse
import logging
import json
import os
import sys
from flask_cors import CORS
from datetime import datetime

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    CORS(app)

    # Startup check
    @app.before_first_request
    def startup_check():
        logger.info("Performing startup checks...")
        try:
            # Log environment information
            logger.info(f"Python version: {sys.version}")
            logger.info(f"Flask version: {Flask.__version__}")
            logger.info(f"Running on port: {os.environ.get('PORT', '8000')}")
            
            # Check if we can make external requests
            test_url = "https://www.google.com"
            requests.get(test_url, timeout=5)
            logger.info("External connectivity check passed")
            
        except Exception as e:
            logger.error(f"Startup check failed: {str(e)}")
            # Don't fail startup, just log the error
    
    @app.route('/health')
    def health_check():
        """Enhanced health check endpoint"""
        try:
            return {
                "status": "healthy",
                "timestamp": str(datetime.now()),
                "python_version": sys.version,
                "flask_version": Flask.__version__,
                "environment": os.environ.get('FLASK_ENV', 'production')
            }, 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": str(datetime.now())
            }, 500

    # Add error handlers
    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Internal server error: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}, 500

    @app.errorhandler(404)
    def handle_404(e):
        return {"error": "Not Found", "message": str(e)}, 404

    @app.errorhandler(502)
    def handle_502(e):
        logger.error(f"Bad Gateway error: {str(e)}")
        return {"error": "Bad Gateway", "message": str(e)}, 502

    @app.route('/')
    def serve_video_library():
        """Serve the video library page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Library</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f0f0f0;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                h1 {
                    color: #333;
                    text-align: center;
                    margin-bottom: 30px;
                }
                .video-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                    padding: 20px;
                }
                .video-card {
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                    cursor: pointer;
                }
                .video-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                }
                .video-thumbnail {
                    width: 100%;
                    height: 180px;
                    background: #ddd;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .video-info {
                    padding: 15px;
                }
                .video-title {
                    margin: 0;
                    font-size: 18px;
                    color: #333;
                }
                .search-bar {
                    margin-bottom: 20px;
                    text-align: center;
                }
                .search-bar input {
                    padding: 10px;
                    width: 300px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin-right: 10px;
                }
                .loading {
                    text-align: center;
                    padding: 20px;
                    font-size: 18px;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Video Library</h1>
                <div class="search-bar">
                    <input type="text" id="searchInput" placeholder="Search videos..." oninput="filterVideos()">
                </div>
                <div id="videoGrid" class="video-grid">
                    <div class="loading">Loading videos...</div>
                </div>
            </div>

            <script>
                // Function to load videos
                async function loadVideos() {
                    try {
                        const response = await fetch('/videos');
                        const videos = await response.json();
                        displayVideos(videos);
                    } catch (error) {
                        console.error('Error loading videos:', error);
                        document.getElementById('videoGrid').innerHTML = 
                            '<div style="color: red; text-align: center;">Error loading videos. Please try again.</div>';
                    }
                }

                // Function to display videos
                function displayVideos(videos) {
                    const grid = document.getElementById('videoGrid');
                    if (videos.length === 0) {
                        grid.innerHTML = '<div style="text-align: center; grid-column: 1/-1;">No videos available</div>';
                        return;
                    }
                    grid.innerHTML = videos.map(video => `
                        <div class="video-card" onclick="playVideo('${video}')">
                            <div class="video-thumbnail">
                                <svg width="64" height="64" viewBox="0 0 24 24" fill="#666">
                                    <path d="M8 5v14l11-7z"/>
                                </svg>
                            </div>
                            <div class="video-info">
                                <h3 class="video-title">${video}</h3>
                            </div>
                        </div>
                    `).join('');
                }

                // Function to filter videos
                function filterVideos() {
                    const search = document.getElementById('searchInput').value.toLowerCase();
                    const cards = document.getElementsByClassName('video-card');
                    
                    for (let card of cards) {
                        const title = card.getElementsByClassName('video-title')[0].textContent.toLowerCase();
                        card.style.display = title.includes(search) ? '' : 'none';
                    }
                }

                // Function to play video
                function playVideo(videoName) {
                    window.location.href = `/player?video=${encodeURIComponent(videoName)}`;
                }

                // Load videos when page loads
                loadVideos();
            </script>
        </body>
        </html>
        """
        return html

    @app.route('/videos')
    def get_videos():
        """Get list of available videos"""
        videos = ['fly', 'song', 'sparkle']
        return json.dumps(videos)

    @app.route('/player')
    def serve_video_player():
        """Serve the video player page"""
        video_name = request.args.get('video')
        if not video_name:
            return "Video name not specified", 400

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Playing {video_name}</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.4.10/hls.min.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    font-family: Arial, sans-serif;
                    background: #f0f0f0;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .video-container {{
                    margin-top: 20px;
                    margin-bottom: 20px;
                }}
                .info-section {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }}
                .error-log {{
                    background: #fff3f3;
                    padding: 10px;
                    margin-top: 10px;
                    border-radius: 4px;
                    display: none;
                }}
                #videoElement {{
                    width: 100%;
                    max-width: 1000px;
                    margin: 0 auto;
                    display: block;
                }}
                .status {{
                    margin-top: 10px;
                    padding: 10px;
                    background: #e8f5e9;
                    border-radius: 4px;
                }}
                .back-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #4a90e2;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-bottom: 20px;
                }}
                .back-button:hover {{
                    background: #357abd;
                }}
                .source-info {{
                    margin-top: 10px;
                    padding: 15px;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                .note {{
                    font-style: italic;
                    color: #666;
                    margin-top: 10px;
                    font-size: 0.9em;
                }}
                code {{
                    background: #eee;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: monospace;
                    word-break: break-all;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-button">← Back to Library</a>
                <h1>Playing: {video_name}</h1>
                
                <div class="video-container">
                    <video id="videoElement" controls></video>
                </div>

                <div class="status" id="status">
                    Status: Initializing player...
                </div>

                <div class="error-log" id="errorLog">
                    <h3>Error Log:</h3>
                    <pre id="errorContent"></pre>
                </div>

                <div class="info-section">
                    <h2>Video Source Information</h2>
                    <div class="source-info">
                        <p><strong>Video Name:</strong> {video_name}</p>
                        <p><strong>Stream Type:</strong> HLS (HTTP Live Streaming)</p>
                        <p><strong>CDN Provider:</strong> Leaseweb CDN</p>
                        <p><strong>Source URL:</strong><br>
                        <code>https://di-yusrkfqf.leasewebultracdn.com/videos/{video_name}/stream.m3u8</code></p>
                        <p class="note">This video is served through Leaseweb's Content Delivery Network (CDN) for optimal streaming performance and global availability.</p>
                    </div>
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const video = document.getElementById('videoElement');
                    const errorLog = document.getElementById('errorLog');
                    const errorContent = document.getElementById('errorContent');
                    const status = document.getElementById('status');
                    
                    function showError(message) {{
                        errorLog.style.display = 'block';
                        errorContent.textContent = message;
                        console.error(message);
                    }}

                    function updateStatus(message) {{
                        status.textContent = 'Status: ' + message;
                        console.log(message);
                    }}

                    if (!window.Hls) {{
                        showError('HLS.js failed to load. Please check your internet connection.');
                        return;
                    }}

                    if (!Hls.isSupported()) {{
                        updateStatus('HLS not supported in this browser');
                        showError('Your browser does not support HLS playback');
                        return;
                    }}

                    const hls = new Hls({{
                        debug: false,
                        enableWorker: true,
                        lowLatencyMode: false,
                        backBufferLength: 90
                    }});

                    hls.on(Hls.Events.MEDIA_ATTACHED, function() {{
                        updateStatus('Media attached, loading manifest...');
                    }});

                    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                        updateStatus('Manifest loaded, starting playback...');
                        video.play().catch(function(error) {{
                            console.warn('Autoplay prevented:', error);
                            updateStatus('Ready to play (click play button)');
                        }});
                    }});

                    hls.on(Hls.Events.ERROR, function(event, data) {{
                        if (data.fatal) {{
                            switch(data.type) {{
                                case Hls.ErrorTypes.NETWORK_ERROR:
                                    updateStatus('Network error, trying to recover...');
                                    hls.startLoad();
                                    break;
                                case Hls.ErrorTypes.MEDIA_ERROR:
                                    updateStatus('Media error, trying to recover...');
                                    hls.recoverMediaError();
                                    break;
                                default:
                                    updateStatus('Fatal error: ' + data.type);
                                    showError('Fatal error: ' + data.details);
                                    break;
                            }}
                        }}
                    }});

                    hls.attachMedia(video);
                    hls.loadSource('/proxy/videos/{video_name}/stream.m3u8');

                    video.addEventListener('playing', function() {{
                        updateStatus('Playing');
                    }});

                    video.addEventListener('waiting', function() {{
                        updateStatus('Buffering...');
                    }});

                    video.addEventListener('error', function(e) {{
                        updateStatus('Video error!');
                        showError('Video Error: ' + e.message);
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html

    @app.route('/proxy/<path:target_path>')
    def proxy_request(target_path):
        """Handle proxy requests to CDN"""
        try:
            logger.info(f"Proxying request for: {target_path}")

            # Extract video name from the path
            path_parts = target_path.split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'videos':
                video_name = path_parts[1]
            else:
                video_name = None

            # Construct the CDN URL
            cdn_url = f"https://di-yusrkfqf.leasewebultracdn.com/{target_path}"
            logger.info(f"Requesting from CDN: {cdn_url}")

            # Set up headers for the CDN request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',  # Prevent gzip encoding
                'Connection': 'keep-alive'
            }

            # Make the request to the CDN
            response = requests.get(cdn_url, headers=headers, timeout=30)
            logger.info(f"CDN response status: {response.status_code}")
            logger.info(f"CDN response headers: {response.headers}")

            if response.status_code == 200:
                content = response.content

                # If this is an m3u8 file, modify the URLs
                if target_path.endswith('.m3u8'):
                    content = modify_m3u8_urls(content.decode('utf-8'), video_name)
                    content = content.encode('utf-8')
                    logger.info(f"Modified m3u8 content: {content.decode('utf-8')}")

                # Determine content type
                content_type = get_content_type(target_path)

                # Create response
                response = Response(content)
                response.headers['Content-Type'] = content_type
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = '*'
                
                return response
            else:
                logger.error(f"CDN returned status {response.status_code}")
                return f"CDN Error: {response.status_code}", response.status_code

        except requests.Timeout:
            logger.error(f"Timeout while fetching: {target_path}")
            return "Gateway Timeout", 504
        except Exception as e:
            logger.error(f"Proxy error: {str(e)}")
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
                    # If it's a segment file and doesn't have the full path
                    if line.startswith('segments/') or line.endswith('.ts'):
                        modified_lines.append(f'/proxy/videos/{video_name}/{line}')
                    else:
                        modified_lines.append(f'/proxy/videos/{video_name}/{line}')
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)
        
        logger.info(f"Modified m3u8 content:\n{'\n'.join(modified_lines)}")
        return '\n'.join(modified_lines)

    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)