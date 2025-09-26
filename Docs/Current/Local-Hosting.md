# Local Podcast Hosting Setup

This document describes the local hosting setup that replaces AWS S3 and external podcast platforms.

## Overview

The podcast generator now runs entirely locally without any cloud dependencies. Audio files are stored locally and served through a local nginx server with a custom podcast hosting service.

## Architecture

### Services

1. **publishing** - Handles publishing episodes to local platforms
2. **podcast-host** - Serves podcast content and generates RSS feeds
3. **nginx** - Serves static files and proxies requests to the podcast-host service

### Local Storage

- Audio files are stored in `/app/storage/episodes/{episode_id}/audio.{format}`
- RSS feeds are generated dynamically
- Podcast pages are served as HTML

## Local Platforms

The publishing service now supports three local platforms:

### 1. local_podcast_host
- Publishes episodes to the local podcast hosting service
- Generates URLs like: `http://localhost:8080/podcast/episodes/{episode_id}`
- Provides HTML pages with embedded audio players

### 2. local_rss_feed
- Generates RSS feeds for episodes
- URLs like: `http://localhost:8080/rss/episodes/{episode_id}`
- Compatible with podcast apps and RSS readers

### 3. local_directory
- Simple directory listing of episodes
- URLs like: `http://localhost:8080/episodes/{episode_id}`
- Provides episode information and download links

## API Endpoints

### Podcast Host Service (port 8006)

- `GET /episodes/{episode_id}` - Get episode information
- `GET /rss/episodes/{episode_id}` - Generate RSS feed
- `GET /podcast/episodes/{episode_id}` - Get podcast page
- `GET /api/episodes` - List all episodes
- `GET /health` - Health check

### Nginx Server (port 8080)

- `GET /storage/episodes/{episode_id}/audio.{format}` - Direct audio file access
- `GET /episodes/{episode_id}` - Episode page (proxied)
- `GET /rss/episodes/{episode_id}` - RSS feed (proxied)
- `GET /podcast/episodes/{episode_id}` - Podcast page (proxied)
- `GET /api/episodes` - API endpoints (proxied)
- `GET /health` - Health check

## Configuration

### Environment Variables

- `LOCAL_STORAGE_PATH` - Path for storing audio files (default: `/app/storage`)
- `LOCAL_SERVER_URL` - Base URL for the nginx server (default: `http://localhost:8080`)

### Storage Structure

```
/app/storage/
├── episodes/
│   └── {episode_id}/
│       └── audio.wav
├── rss/
└── podcast/
```

## Usage

### Publishing an Episode

```python
# Example publishing request
request = PublishRequest(
    episode_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    platforms=["local_podcast_host", "local_rss_feed", "local_directory"],
    platform_credentials={
        "local_podcast_host": {},
        "local_rss_feed": {},
        "local_directory": {}
    }
)
```

### Accessing Published Content

1. **Podcast Page**: `http://localhost:8080/podcast/episodes/{episode_id}`
2. **RSS Feed**: `http://localhost:8080/rss/episodes/{episode_id}`
3. **Direct Audio**: `http://localhost:8080/storage/episodes/{episode_id}/audio.wav`
4. **Episode Info**: `http://localhost:8080/episodes/{episode_id}`

## Benefits

1. **No Cloud Dependencies** - Runs entirely locally
2. **No External APIs** - No need for AWS credentials or external service accounts
3. **Full Control** - Complete control over hosting and content delivery
4. **Privacy** - All content stays on your local network
5. **Cost Effective** - No cloud storage or bandwidth costs

## Migration from AWS

The publishing service has been completely rewritten to remove AWS dependencies:

- ❌ Removed `boto3` dependency
- ❌ Removed S3 upload functionality
- ✅ Added local file storage with `LocalFileManager`
- ✅ Added local podcast hosting service
- ✅ Added nginx for file serving and proxying
- ✅ Updated platform configurations for local hosting

## Development

To test the local hosting setup:

1. Start the services: `docker-compose up`
2. Test publishing: `POST /publish` with local platforms
3. Access content: Visit the generated URLs in your browser
4. Check RSS feeds: Use an RSS reader or podcast app

## Troubleshooting

### Common Issues

1. **Storage directory not found**: Ensure the `storage_data` volume is mounted correctly
2. **Audio files not accessible**: Check nginx configuration and file permissions
3. **RSS feeds not working**: Verify the podcast-host service is running and accessible
4. **Proxy errors**: Check nginx logs and ensure the podcast-host service is healthy

### Logs

- Publishing service: `docker-compose logs publishing`
- Podcast host: `docker-compose logs podcast-host`
- Nginx: `docker-compose logs nginx`

### Health Checks

- Publishing service: `http://localhost:8005/health`
- Podcast host: `http://localhost:8006/health`
- Nginx: `http://localhost:8080/health`
