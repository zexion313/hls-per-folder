import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Leaseweb Object Storage Configuration
LEASEWEB_CONFIG = {
    'endpoint_url': 'https://nl.object-storage.io',
    'bucket_name': 'private-bucket-nl',
    'access_key': os.getenv('LEASEWEB_ACCESS_KEY'),  # This will now load from .env file
    'secret_key': os.getenv('LEASEWEB_SECRET_KEY'),  # This will now load from .env file
    'region': 'nl'
}

# Directory Configuration
INPUT_DIR = BASE_DIR / 'input'
OUTPUT_DIR = BASE_DIR / 'output'

# FFmpeg Configuration
FFMPEG_PATH = r"C:\ffmpeg\ffmpeg.exe"
SEGMENT_DURATION = 6
KEY_LENGTH = 16  # 128-bit key 