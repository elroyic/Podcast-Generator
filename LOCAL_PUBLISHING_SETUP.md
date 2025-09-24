# Local Publishing Setup

This document describes the changes made to replace AWS S3 with locally hosted services for podcast publishing.

## Changes Made

### 1. Infrastructure Changes

#### Added Services to docker-compose.yml:
- **MinIO**: S3-compatible object storage running locally
- **File Server**: Nginx-based HTTP server for serving uploaded files
- **Updated Publishing Service**: Modified to use local storage instead of AWS S3

#### New Environment Variables:
- `MINIO_ENDPOINT`: MinIO server endpoint (default: http://minio:9000)
- `MINIO_ACCESS_KEY`: MinIO access key (default: minioadmin)
- `MINIO_SECRET_KEY`: MinIO secret key (default: minioadmin)
- `MINIO_BUCKET`: MinIO bucket name (default: podcast-storage)
- `FILE_SERVER_URL`: File server URL (default: http://file-server:8080)

### 2. Code Changes

#### Publishing Service (services/publishing/main.py):
- Replaced `boto3` with `minio` library
- Replaced `S3Uploader` class with `LocalFileUploader` class
- Updated file upload logic to use MinIO for storage and file server for serving
- Removed AWS-specific configuration and dependencies

#### Dependencies (services/publishing/requirements.txt):
- Removed: `boto3==1.34.0`
- Added: `minio==7.2.0`

### 3. New Files

#### nginx.conf:
- Configuration for the file server
- Enables CORS for cross-origin requests
- Sets up proper MIME types for audio files
- Includes caching headers for static files

#### test_local_publishing.py:
- Test script to verify the local publishing setup
- Tests MinIO connection and file operations
- Tests file server accessibility
- Tests publishing service endpoints

## How It Works

1. **File Upload Process**:
   - Audio files are uploaded to MinIO (S3-compatible storage)
   - Files are also copied to the file server directory for direct HTTP access
   - Public URLs are generated using the file server endpoint

2. **File Serving**:
   - MinIO provides object storage with S3-compatible API
   - Nginx file server provides direct HTTP access to files
   - Files are accessible via URLs like: `http://localhost:8080/episodes/{episode_id}/audio.wav`

3. **Publishing Flow**:
   - Publishing service receives episode data
   - Audio files are uploaded to local storage
   - Public URLs are generated for podcast platforms
   - Episode metadata and audio URLs are sent to external platforms

## Running the System

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Access services**:
   - MinIO Console: http://localhost:9001 (admin/minioadmin)
   - File Server: http://localhost:8080
   - Publishing Service: http://localhost:8005

3. **Test the setup**:
   ```bash
   python test_local_publishing.py
   ```

## Benefits of Local Setup

1. **No Cloud Dependencies**: Everything runs locally without external services
2. **Cost Effective**: No AWS S3 storage costs
3. **Privacy**: All data stays on your local infrastructure
4. **Control**: Full control over storage and file serving
5. **Development Friendly**: Easy to test and debug locally

## File Storage Structure

```
MinIO Bucket: podcast-storage/
├── episodes/
│   └── {episode_id}/
│       └── audio.{format}

File Server: /usr/share/nginx/html/
├── episodes/
│   └── {episode_id}/
│       └── audio.{format}
```

## Troubleshooting

### MinIO Issues:
- Check if MinIO is running: `docker-compose ps minio`
- Verify bucket exists in MinIO console
- Check MinIO logs: `docker-compose logs minio`

### File Server Issues:
- Check if nginx is running: `docker-compose ps file-server`
- Verify file permissions in the file server volume
- Check nginx logs: `docker-compose logs file-server`

### Publishing Service Issues:
- Check service logs: `docker-compose logs publishing`
- Verify environment variables are set correctly
- Test individual endpoints with curl or the test script

## Migration Notes

If you were previously using AWS S3:
1. All existing episode data will continue to work
2. New episodes will use local storage
3. Old S3 URLs will need to be migrated if you want to serve them locally
4. Consider setting up a migration script if you have existing files in S3