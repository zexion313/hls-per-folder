import boto3
from botocore.client import Config
from pathlib import Path
import os

class LeasewebStorageHandler:
    def __init__(self, config):
        self.session = boto3.client(
            's3',
            endpoint_url=config['endpoint_url'],
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=config['region'],
            config=Config(signature_version='s3v4')
        )
        self.bucket = config['bucket_name']

    def check_connection(self):
        """Check if we can connect to the storage bucket"""
        try:
            self.session.head_bucket(Bucket=self.bucket)
            print("Successfully connected to Leaseweb Storage!")
            return True
        except Exception as e:
            print(f"Failed to connect to Leaseweb Storage: {str(e)}")
            return False

    def upload_file(self, local_path: str, object_key: str) -> bool:
        """Upload a single file to storage"""
        try:
            print(f"Uploading {local_path} to {object_key}...")
            self.session.upload_file(local_path, self.bucket, object_key)
            print(f"Successfully uploaded {object_key}")
            return True
        except Exception as e:
            print(f"Failed to upload {object_key}: {str(e)}")
            return False

    def upload_video_files(self, video_name: str, video_dir: Path) -> bool:
        """Upload all files related to a video"""
        try:
            # 1. Upload key file
            key_file = video_dir / "key.key"
            if key_file.exists():
                self.upload_file(
                    str(key_file),
                    f"videos/{video_name}/key.key"
                )

            # 2. Upload segments
            segments_dir = video_dir / "segments"
            for segment in segments_dir.glob("*.ts"):
                self.upload_file(
                    str(segment),
                    f"videos/{video_name}/segments/{segment.name}"
                )

            # 3. Upload playlist files
            for playlist in ["stream.m3u8", "iframes.m3u8"]:
                playlist_file = video_dir / playlist
                if playlist_file.exists():
                    self.upload_file(
                        str(playlist_file),
                        f"videos/{video_name}/{playlist}"
                    )

            print(f"Successfully uploaded all files for {video_name}")
            return True

        except Exception as e:
            print(f"Error uploading video files for {video_name}: {str(e)}")
            return False

    def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for an object"""
        try:
            url = self.session.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {str(e)}")
            return None 