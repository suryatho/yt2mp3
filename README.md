# SpotifyTool

A powerful browser extension and server system for downloading audio from YouTube and SoundCloud platforms.

## 🚀 Features

- **Multi-Platform Support**: Download audio from YouTube and SoundCloud
- **Browser Extension**: Chrome extension with seamless integration
- **Concurrent Downloads**: Handle multiple downloads simultaneously
- **Smart Notifications**: Real-time download status with Chrome notifications
- **Metadata Embedding**: Automatic title, artist, and thumbnail embedding
- **Background Processing**: Downloads continue even when browser tab is closed

## 📦 Components

### Chrome Extension (`spotify-tool-extension/`)
- **Manifest V3** browser extension
- Content scripts for YouTube and SoundCloud injection
- Real-time download tracking popup
- Background service worker for notifications

### Server (`core/`)
- **FastAPI** backend with async processing
- **yt-dlp** integration for YouTube downloads
- **scdl** support for SoundCloud downloads
- **FFmpeg** for audio processing and metadata embedding

### CLI Tool
- Command-line interface for direct downloads
- Standalone usage without browser extension

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- FFmpeg
- yt-dlp
- scdl (for SoundCloud)

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd spotifytool
   ```

2. **Install the server**
   ```bash
   ./setup_server.sh
   ```

3. **Install the Chrome extension**
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `spotify-tool-extension/` folder

### Manual Installation

#### Server Setup
```bash
# Install with pipx (recommended)
pipx install -e .

# Or install with pip
pip install -e .

# Start the server
spotifytool-server
```

#### Development Setup
```bash
# Install development dependencies
./setup_dev.sh

# Run server in development mode
python -m core.server
```

## 🎯 Usage

### Browser Extension
1. Navigate to a YouTube video or SoundCloud track
2. Click the download button injected by the extension
3. Monitor download progress via notifications
4. Files are saved to `~/Documents/Spotify/`

### Command Line
```bash
# Download a single URL
spotifytool "https://www.youtube.com/watch?v=VIDEO_ID"

# Start the server manually
spotifytool-server
```

### API Usage
```bash
# Health check
curl http://localhost:5000/health

# Download via API
curl -X POST -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}' \
     http://localhost:5000/download
```

## 📁 Project Structure

```
spotifytool/
├── spotify-tool-extension/          # Chrome extension
│   ├── manifest.json               # Extension manifest
│   ├── background.js              # Service worker
│   ├── content.js                 # YouTube content script
│   ├── content-soundcloud.js      # SoundCloud content script
│   └── popup/                     # Extension popup UI
│       ├── popup.html
│       ├── popup.js
│       └── popup.css
├── core/                          # Python backend
│   ├── server.py                  # FastAPI server
│   ├── downloader.py             # Download logic
│   └── cli.py                    # CLI interface
├── setup_server.sh               # Server setup script
├── setup_dev.sh                 # Development setup
├── pyproject.toml               # Python project config
└── README.md                    # This file
```

## ⚙️ Configuration

### Server Configuration
The server runs on `http://localhost:5000` by default and logs to `/tmp/spotifytool-server.log`.

### Download Directory
Files are downloaded to `~/Documents/Spotify/` by default.

### Extension Permissions
The extension requires:
- `activeTab` - Access current tab for content injection
- `notifications` - Show download status notifications  
- `scripting` - Inject content scripts
- `host_permissions` - Access YouTube and SoundCloud domains

## 🔧 Development





## 📝 API Reference

### Health Check
```http
GET /health
```
Returns: `{"status": "online"}`

### Download Audio
```http
POST /download
Content-Type: application/json

{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "title": "Optional custom title"
}
```

Returns:
```json
{
    "status": "success",
    "message": "Download completed in X.Xs"
}
```

## � Key Dependencies

- **yt-dlp**: YouTube video/audio extraction  
- **FFmpeg**: Audio processing and metadata embedding
- **scdl**: SoundCloud downloading
- **FastAPI**: Web server framework