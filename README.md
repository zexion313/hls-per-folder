# HLS Video Processor V2

Enhanced version of the HLS video processor with separate storage buckets for control files and video segments.

## Features

- Separate storage for control files (m3u8, keys) and video segments
- Enhanced security with private control bucket
- Optimized CDN delivery for video segments
- Improved error handling and logging
- Support for multiple storage configurations

## Setup

1. Create two S3-compatible buckets:
   - `hls-control-files`: For control files (m3u8, keys)
   - `hls-segments-cdn`: For video segments

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env`:
   ```env
   LEASEWEB_ENDPOINT_URL=your_endpoint_url
   LEASEWEB_ACCESS_KEY=your_access_key
   LEASEWEB_SECRET_KEY=your_secret_key
   LEASEWEB_REGION=your_region
   LEASEWEB_CONTROL_BUCKET=hls-control-files
   LEASEWEB_CDN_BUCKET=hls-segments-cdn
   ```

4. Place your MP4 files in the `input` directory

5. Run the processor:
   ```bash
   python generate.py
   ```

## Directory Structure

```
hls-video-processor-v2/
├── input/              # Place MP4 files here
├── output/             # Temporary processing directory
├── test_players/       # Test player files
├── config.py           # Configuration settings
├── storage_handler.py  # Storage management
├── generate.py         # Main processing script
└── requirements.txt    # Python dependencies
```

## Storage Architecture

- **Control Files Bucket (`hls-control-files`)**
  - stream.m3u8
  - iframes.m3u8
  - key.key

- **CDN Bucket (`hls-segments-cdn`)**
  - Video segments (.ts files)

## Security

- Control files are stored in a private bucket
- Segment files are stored in a CDN-enabled bucket
- Access to control files is managed through the application
- Segments are publicly accessible through CDN

## License

MIT 