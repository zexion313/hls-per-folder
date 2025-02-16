import http.server
import socketserver
import os
from pathlib import Path
import mimetypes
import socket

PORT = 8000

class HLSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Add HLS mime types
        mimetypes.add_type('application/vnd.apple.mpegurl', '.m3u8')
        mimetypes.add_type('video/mp2t', '.ts')
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        
        # Add caching headers for different file types
        ext = os.path.splitext(self.path)[1]
        if ext == '.m3u8':
            self.send_header('Cache-Control', 'no-cache')
        elif ext == '.ts':
            self.send_header('Cache-Control', 'public, max-age=31536000')
        
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def guess_type(self, path):
        """Override the mime type for m3u8 and ts files."""
        ext = os.path.splitext(path)[1]
        if ext == '.m3u8':
            return 'application/vnd.apple.mpegurl'
        elif ext == '.ts':
            return 'video/mp2t'
        return super().guess_type(path)

    def handle(self):
        try:
            super().handle()
        except (socket.error, ConnectionAbortedError) as e:
            # Ignore client disconnection errors
            pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    # Change to the directory containing this script
    os.chdir(Path(__file__).parent)
    
    handler = HLSRequestHandler
    with ThreadedHTTPServer(("", PORT), handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Video player available at: http://localhost:{PORT}/player.html")
        print("Press Ctrl+C to stop the server...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    main()
