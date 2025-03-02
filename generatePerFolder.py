import os
import sys
import secrets
import subprocess
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional
from config import INPUT_DIR, OUTPUT_DIR, FFMPEG_PATH, SEGMENT_DURATION, KEY_LENGTH, LEASEWEB_PRIVATE_CONFIG
from folder_storage_handler import FolderStorageHandler

class VideoProcessor:
    def __init__(self, input_dir: str, output_dir: str, storage_handler: FolderStorageHandler):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.storage = storage_handler

    def test_storage_connection(self) -> bool:
        """Test connection to storage and basic operations"""
        print("\n=== Testing Storage Connection ===")
        
        # 1. Test basic connection
        if not self.storage.check_connection():
            print("❌ Basic connection test failed!")
            return False
        print("✓ Basic connection test passed!")

        # 2. Test presigned URL generation
        print("\nTesting presigned URL generation...")
        test_url = self.storage.generate_presigned_url("test.txt", folder=self.storage.key_folder)
        if not test_url:
            print("❌ Presigned URL generation test failed!")
            return False
        print("✓ Presigned URL generation test passed!")
        print(f"Sample presigned URL: {test_url}")

        print("\n✓ All storage tests passed successfully!")
        return True

    def validate_environment(self) -> bool:
        """Validate all required components"""
        print("\n=== Validating Environment ===")
        
        # 1. Check FFmpeg
        if not os.path.exists(FFMPEG_PATH):
            print("❌ FFmpeg not found at:", FFMPEG_PATH)
            return False
        print("✓ FFmpeg found!")

        # 2. Check input directory
        if not self.input_dir.exists():
            print(f"Creating input directory at {self.input_dir}")
            self.input_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Input directory ready!")

        # 3. Check output directory
        if not self.output_dir.exists():
            print(f"Creating output directory at {self.output_dir}")
            self.output_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Output directory ready!")

        return True

    def _generate_key(self) -> tuple[bytes, str]:
        """Generate encryption key and key URL with UUID-based filename."""
        key = secrets.token_bytes(KEY_LENGTH)
        key_filename = f"{uuid.uuid4()}.key"
        return key, key_filename

    def _setup_video_directory(self, video_name: str) -> Path:
        """Create output directory structure for a video."""
        video_dir = self.output_dir / video_name
        
        # Clean up any existing directory
        if video_dir.exists():
            shutil.rmtree(video_dir)
        
        # Create directory
        video_dir.mkdir(parents=True, exist_ok=True)
        
        return video_dir

    def _write_key_file(self, video_dir, key, key_filename):
        """Write the key file and key info file."""
        # Write the key to a file
        key_path = video_dir / key_filename
        with open(key_path, 'wb') as f:
            f.write(key)
        
        # Write the key info file
        key_info_path = video_dir / "key_info"
        with open(key_info_path, 'w') as f:
            f.write(f"{key_filename}\n{str(key_path)}\n")
            
        return key_info_path

    def _create_iframe_playlist(self, input_file, video_dir, key_info_path, video_name):
        """Create an iframe playlist for the video."""
        print("2. Generating iframe playlist...")
        output_ts = video_dir / f"{video_name}.ts"
        
        # Create a temporary playlist file
        temp_playlist = video_dir / "iframe_temp.m3u8"
        
        # Generate a basic HLS playlist with single file
        iframe_cmd = [
            FFMPEG_PATH,
            "-i", str(input_file),
            "-c:v", "copy",
            "-c:a", "copy",
            "-force_key_frames", "expr:gte(t,n_forced*1)",
            "-f", "hls",
            "-hls_time", str(SEGMENT_DURATION),
            "-movflags", "+faststart",
            "-hls_segment_type", "mpegts",
            "-hls_list_size", "0",
            "-hls_flags", "single_file",
            "-hls_key_info_file", str(key_info_path),
            "-hls_playlist_type", "vod",
            str(temp_playlist)
        ]
        
        print(f"Running iframe FFmpeg command: {' '.join(iframe_cmd)}")
        result = subprocess.run(iframe_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg iframe error: {result.stderr}")
            raise Exception(f"FFmpeg iframe command failed: {result.stderr}")
        
        print(f"FFmpeg iframe output: {result.stdout[:200]}...")  # Show first 200 chars of output
        
        # Check if temp playlist was created
        if not temp_playlist.exists():
            print(f"Warning: {temp_playlist} was not created!")
            raise Exception(f"Temporary iframe playlist was not created")
        
        # Now modify the playlist to make it an iframe-only playlist
        try:
            with open(temp_playlist, "r") as f:
                content = f.read()
            
            # Add the I-FRAMES-ONLY tag after the version tag
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-VERSION:'):
                    lines.insert(i + 1, '#EXT-X-I-FRAMES-ONLY')
                    break
            
            # Write the modified content to the final iframe.m3u8 file
            with open(video_dir / "iframe.m3u8", "w") as f:
                f.write('\n'.join(lines))
            
            # Remove the temporary file
            os.remove(temp_playlist)
            
            # Also remove the temporary TS file created for the iframe playlist
            temp_ts = video_dir / "iframe_temp0.ts"
            if temp_ts.exists():
                os.remove(temp_ts)
                print(f"Removed temporary TS file: {temp_ts}")
            
            print("✓ Iframe playlist generated!")
        except Exception as e:
            print(f"Error modifying iframe playlist: {str(e)}")
            raise

    def process_video(self, input_file: Path):
        """Process a single video file."""
        try:
            video_name = input_file.stem
            print(f"\nProcessing video: {video_name}")
            
            # Setup directory and generate key
            video_dir = self._setup_video_directory(video_name)
            print(f"Created video directory: {video_dir}")
            
            key, key_filename = self._generate_key()
            print(f"Generated key with filename: {key_filename}")
            
            key_info_path = self._write_key_file(video_dir, key, key_filename)
            print(f"Wrote key info file at: {key_info_path}")
            
            # Generate main stream playlist with single file
            print("1. Generating main stream playlist with single file...")
            output_ts = video_dir / f"{video_name}.ts"
            stream_cmd = [
                FFMPEG_PATH,
                "-i", str(input_file),
                "-c:v", "copy", 
                "-c:a", "copy",
                "-force_key_frames", "expr:gte(t,n_forced*1)",
                "-f", "hls",
                "-hls_time", str(SEGMENT_DURATION),
                "-movflags", "+faststart",
                "-hls_segment_type", "mpegts",
                "-hls_list_size", "0",
                "-hls_flags", "single_file",
                "-hls_key_info_file", str(key_info_path),
                "-hls_playlist_type", "vod",
                str(video_dir / "stream.m3u8")
            ]
            
            print(f"Running FFmpeg command: {' '.join(stream_cmd)}")
            result = subprocess.run(stream_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg command failed: {result.stderr}")
            
            print(f"FFmpeg output: {result.stdout[:200]}...")  # Show first 200 chars of output
            print("✓ Main stream playlist generated!")
            
            # Check if files were created
            if not (video_dir / "stream.m3u8").exists():
                print(f"Warning: stream.m3u8 was not created!")
            else:
                print(f"stream.m3u8 was created successfully, size: {os.path.getsize(video_dir / 'stream.m3u8')} bytes")
                
            # In single file mode, FFmpeg creates a file named stream0.ts
            ts_file = video_dir / "stream0.ts"
            if not ts_file.exists():
                print(f"Warning: {ts_file.name} was not created!")
            else:
                print(f"{ts_file.name} was created successfully, size: {os.path.getsize(ts_file)} bytes")
                # Rename to video_name.ts
                ts_file.rename(output_ts)
                print(f"Renamed {ts_file.name} to {output_ts.name}")
            
            # Generate iframe playlist
            self._create_iframe_playlist(input_file, video_dir, key_info_path, video_name)
            
            # Check if iframe playlist was created
            if not (video_dir / "iframe.m3u8").exists():
                print(f"Warning: iframe.m3u8 was not created!")
            else:
                print(f"iframe.m3u8 was created successfully, size: {os.path.getsize(video_dir / 'iframe.m3u8')} bytes")
            
            # Upload to storage
            print("3. Uploading files to storage...")
            success = self.storage.upload_video_files(video_dir, video_name, key_filename)
            if success:
                print("✓ Files uploaded to storage!")
            else:
                print("❌ Failed to upload some files to storage!")
                return False, f"Failed to upload files for {video_name}"
            
            # List all files in the directory
            print(f"Files in {video_dir}:")
            for file in video_dir.glob("*"):
                print(f"  - {file.name} ({os.path.getsize(file)} bytes)")
            
            return True, f"Successfully processed {video_name}"
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Error processing {input_file.name}: {str(e)}"

    def process_all_videos(self) -> bool:
        """Process all MP4 files in the input directory."""
        mp4_files = list(self.input_dir.glob("*.mp4"))
        
        if not mp4_files:
            print("\n❌ No MP4 files found in input directory.")
            print(f"Please place MP4 files in: {self.input_dir}")
            return False

        print(f"\nFound {len(mp4_files)} MP4 files to process.")
        
        successful = 0
        results = []
        
        for input_file in mp4_files:
            success, message = self.process_video(input_file)
            results.append((input_file.name, success, message))
            if success:
                successful += 1

        print(f"\n=== Processing Summary ===")
        print(f"Total videos: {len(mp4_files)}")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {len(mp4_files) - successful}")
        
        if len(mp4_files) - successful > 0:
            print("\nFailed videos:")
            for name, success, message in results:
                if not success:
                    print(f"  - {name}: {message}")
        
        return successful == len(mp4_files)

def main():
    """Main entry point for the script."""
    print("\n=== Video Processing System (Single-File HLS with Folder Organization) ===")
    
    try:
        # Step 1: Initialize storage handler with private bucket configuration
        storage = FolderStorageHandler(LEASEWEB_PRIVATE_CONFIG)
        
        # Step 2: Initialize video processor
        processor = VideoProcessor(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            storage_handler=storage
        )
        
        # Step 3: Validate environment
        if not processor.validate_environment():
            print("\n❌ Environment validation failed. Please fix the issues and try again.")
            return 1
        
        # Step 4: Test storage connection
        if not processor.test_storage_connection():
            print("\n❌ Storage connection test failed. Please check your credentials and try again.")
            return 1
        
        # Step 5: Process all videos
        print("\n=== Starting Video Processing (Single-File HLS with Folder Organization) ===")
        if not processor.process_all_videos():
            print("\n⚠️ Some videos failed to process. Check the logs for details.")
            return 1
        
        print("\nDone!")
        return 0
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
