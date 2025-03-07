import os
import requests
import webbrowser
import time
import subprocess
import sys
from urllib.parse import urljoin

class HLSPlayer:
    def __init__(self):
        self.cdn_base_url = "https://di-yusrkfqf.leasewebultracdn.com"
        self.m3u8_folder = "Example_folder_for_m3u8"
        self.server_url = "http://localhost:8000"
        
        # List of known videos - we can add more as needed
        self.video_ids = ['android', 'maverick']
        
    def check_server(self):
        """Check if the Flask server is running"""
        try:
            response = requests.get(self.server_url, timeout=2)
            return response.status_code == 200
        except:
            return False

    def start_server(self):
        """Start the Flask server"""
        print("\nStarting Flask server...")
        try:
            # Check if we have Flask installed
            import flask
        except ImportError:
            print("Error: Flask is not installed. Please run:")
            print("pip install -r requirements.txt")
            return False

        if sys.platform == 'win32':
            # For Windows, use start command to open in new window
            subprocess.Popen('start cmd /k python app.py', shell=True)
        else:
            # For Unix-like systems
            subprocess.Popen(['python', 'app.py'])
        
        # Wait for server to start
        print("Waiting for server to start...")
        for _ in range(5):  # Try for 5 seconds
            if self.check_server():
                print("Server is running!")
                return True
            time.sleep(1)
        
        print("Error: Could not start server. Please run manually:")
        print("python app.py")
        return False

    def scan_videos(self):
        """Scan for available videos in CDN"""
        videos = []
        
        for video_id in self.video_ids:
            # Construct m3u8 URL
            m3u8_url = f"{self.cdn_base_url}/{self.m3u8_folder}/{video_id}/stream.m3u8"
            
            # Get video information
            video_info = self.get_video_info(video_id, m3u8_url)
            if video_info:
                videos.append(video_info)
        
        return videos
    
    def get_video_info(self, video_id, m3u8_url):
        """Extract video information from m3u8 URL"""
        try:
            # Fetch m3u8 content from CDN
            response = requests.get(m3u8_url)
            if response.status_code != 200:
                print(f"Error fetching {m3u8_url}: Status {response.status_code}")
                return None
                
            content = response.text
            
            # Get duration from m3u8 content (sum of segment durations)
            duration = 0
            for line in content.split('\n'):
                if line.startswith('#EXTINF:'):
                    try:
                        # Remove any trailing comma and convert to float
                        duration += float(line.split(':')[1].split(',')[0])
                    except (IndexError, ValueError) as e:
                        print(f"Error parsing duration: {str(e)}")
                        continue
            
            return {
                'id': video_id,
                'name': video_id.capitalize(),
                'duration': self.format_duration(duration),
                'file_size': "Streaming from CDN",
                'm3u8_url': m3u8_url
            }
        except Exception as e:
            print(f"Error processing {video_id}: {str(e)}")
            return None
    
    def format_duration(self, seconds):
        """Format duration in seconds to MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def play_video(self, video_info):
        """Open video in web browser"""
        try:
            # Check if server is running
            if not self.check_server():
                print("\nWeb server is not running!")
                if not self.start_server():
                    print("Could not start web server. Please start it manually:")
                    print("python app.py")
                    return
                # Give the server a moment to initialize
                time.sleep(2)
            
            # Open the web player with the video
            url = f'{self.server_url}?video={video_info["id"]}'
            webbrowser.open(url)
            print(f"\nOpening web player...")
            print(f"Playing: {video_info['name']}")
            print(f"Duration: {video_info['duration']}")
            print(f"M3U8 URL: {video_info['m3u8_url']}")
            
        except Exception as e:
            print(f"Error playing video: {str(e)}")

def main():
    player = HLSPlayer()
    
    while True:
        print("\nHLS Video Player Test Environment")
        print("=================================")
        
        # Scan for videos
        videos = player.scan_videos()
        
        if not videos:
            print("No videos found or accessible in CDN!")
            break
        
        # Display video list
        print("\nAvailable Videos:")
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['name']} ({video['duration']})")
        
        print("\nOptions:")
        print("0. Exit")
        
        try:
            choice = int(input("\nEnter video number to play (0 to exit): "))
            if choice == 0:
                break
            elif 1 <= choice <= len(videos):
                player.play_video(videos[choice - 1])
            else:
                print("Invalid choice!")
        except ValueError:
            print("Please enter a valid number!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 