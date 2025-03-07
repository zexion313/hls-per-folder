import boto3
from botocore.client import Config
from pathlib import Path
import os

class LeasewebStorageHandler:
    def __init__(self, control_config, cdn_config):
        # Initialize control bucket client
        self.control_session = boto3.client(
            's3',
            endpoint_url=control_config['endpoint_url'],
            aws_access_key_id=control_config['access_key'],
            aws_secret_access_key=control_config['secret_key'],
            region_name=control_config['region'],
            config=Config(signature_version='s3v4')
        )
        self.control_bucket = control_config['bucket_name']

        # Initialize CDN bucket client
        self.cdn_session = boto3.client(
            's3',
            endpoint_url=cdn_config['endpoint_url'],
            aws_access_key_id=cdn_config['access_key'],
            aws_secret_access_key=cdn_config['secret_key'],
            region_name=cdn_config['region'],
            config=Config(signature_version='s3v4')
        )
        self.cdn_bucket = cdn_config['bucket_name']

    def check_connection(self):
        """Check if we can connect to both storage buckets"""
        try:
            # Check control bucket
            self.control_session.head_bucket(Bucket=self.control_bucket)
            print("Successfully connected to Control Storage!")

            # Check CDN bucket
            self.cdn_session.head_bucket(Bucket=self.cdn_bucket)
            print("Successfully connected to CDN Storage!")
            
            return True
        except Exception as e:
            print(f"Failed to connect to storage: {str(e)}")
            return False

    def upload_control_file(self, local_path: str, object_key: str) -> bool:
        """Upload control files (m3u8, key) to control bucket"""
        try:
            print(f"Uploading control file {local_path} to {object_key}...")
            self.control_session.upload_file(local_path, self.control_bucket, object_key)
            print(f"Successfully uploaded control file {object_key}")
            return True
        except Exception as e:
            print(f"Failed to upload control file {object_key}: {str(e)}")
            return False

    def upload_segment_file(self, local_path: str, object_key: str) -> bool:
        """Upload segment files to CDN bucket"""
        try:
            print(f"Uploading media file {local_path} to {object_key}...")
            self.cdn_session.upload_file(local_path, self.cdn_bucket, object_key)
            print(f"Successfully uploaded media file {object_key}")
            return True
        except Exception as e:
            print(f"Failed to upload media file {object_key}: {str(e)}")
            return False

    def upload_video_files(self, video_dir: Path, video_name: str, key_filename: str) -> bool:
        """Upload all files related to a video to their respective buckets"""
        try:
            # 1. Upload control files (m3u8, key) to control bucket
            control_files = [
                (video_dir / key_filename, f"videos/{video_name}/{key_filename}"),
                (video_dir / "stream.m3u8", f"videos/{video_name}/stream.m3u8"),
                (video_dir / "iframe.m3u8", f"videos/{video_name}/iframe.m3u8")
            ]

            for local_file, object_key in control_files:
                if local_file.exists():
                    if not self.upload_control_file(str(local_file), object_key):
                        return False
                else:
                    print(f"Warning: Control file {local_file} does not exist, skipping upload")

            # 2. Upload media files to CDN bucket
            # First check for the video_name.ts file
            ts_file = video_dir / f"{video_name}.ts"
            
            # If not found, check for stream0.ts (FFmpeg default output)
            if not ts_file.exists():
                ts_file = video_dir / "stream0.ts"
                if not ts_file.exists():
                    # If still not found, look for any .ts files
                    ts_files = list(video_dir.glob("*.ts"))
                    if ts_files:
                        ts_file = ts_files[0]
                    else:
                        print(f"Error: No .ts files found for {video_name}")
                        return False
            
            # Upload the TS file
            object_key = f"videos/{video_name}/{video_name}.ts"
            if not self.upload_segment_file(str(ts_file), object_key):
                return False

            print(f"Successfully uploaded all files for {video_name}")
            return True

        except Exception as e:
            print(f"Error uploading video files for {video_name}: {str(e)}")
            return False

    def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for an object from the control bucket"""
        try:
            url = self.control_session.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.control_bucket,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {str(e)}")
            return None 