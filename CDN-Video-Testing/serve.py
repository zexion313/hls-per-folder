import http.server
import socketserver
import requests
import urllib.parse
import logging
import json
import threading
from http import HTTPStatus

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

class ProxyCORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Max-Age', '86400')

    def serve_video_library(self):
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
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_video_player(self, video_name):
        """Serve the video player page"""
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
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        try:
            # Parse the URL
            parsed_url = urllib.parse.urlparse(self.path)
            
            # Route requests
            if parsed_url.path == '/':
                self.serve_video_library()
                return
            elif parsed_url.path == '/videos':
                # Serve list of videos
                videos = self.get_available_videos()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                content = json.dumps(videos).encode()
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                return
            elif parsed_url.path == '/player':
                # Get video name from query parameters
                query_params = urllib.parse.parse_qs(parsed_url.query)
                video_name = query_params.get('video', [''])[0]
                if video_name:
                    self.serve_video_player(video_name)
                    return
                else:
                    self.send_error(400, "Video name not specified")
                    return
            elif parsed_url.path.startswith('/proxy/'):
                # Handle proxy requests
                try:
                    target_path = self.path[7:]  # Remove '/proxy/' prefix
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
                            content = self.modify_m3u8_urls(content.decode('utf-8'), video_name)
                            content = content.encode('utf-8')
                            logger.info(f"Modified m3u8 content: {content.decode('utf-8')}")

                        # Send the response
                        self.send_response(200)
                        self.send_header('Content-Type', self.get_content_type(target_path))
                        self.send_header('Content-Length', len(content))
                        self.send_cors_headers()
                        self.end_headers()
                        self.wfile.write(content)
                    else:
                        logger.error(f"CDN returned status {response.status_code}")
                        self.send_error(response.status_code)

                except requests.Timeout:
                    logger.error(f"Timeout while fetching: {target_path}")
                    self.send_error(504, "Gateway Timeout")
                except Exception as e:
                    logger.error(f"Proxy error: {str(e)}")
                    self.send_error(500, str(e))
                return

            else:
                self.send_error(404, "Not found")
                return

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_error(500, str(e))

    def get_content_type(self, path):
        """Determine content type based on file extension"""
        if path.endswith('.m3u8'):
            return 'application/vnd.apple.mpegurl'
        elif path.endswith('.ts'):
            return 'video/mp2t'
        elif path.endswith('.key'):
            return 'application/octet-stream'
        else:
            return 'application/octet-stream'

    def modify_m3u8_urls(self, content, video_name=None):
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

    def get_available_videos(self):
        """Get list of available videos"""
        # Return the list of videos you want to make available
        return ['fly', 'song', 'sparkle']  # Add your video names here

def run_server(port=8000):
    """Run the HTTP server"""
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, ProxyCORSRequestHandler)
    
    logger.info(f"Server running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        httpd.shutdown()
        httpd.server_close()

if __name__ == "__main__":
    run_server()