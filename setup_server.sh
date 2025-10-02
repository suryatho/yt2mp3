#!/bin/bash
# filepath: /Users/surya/Developer/spotifytool/setup_server.sh

set -e  # Exit on error
set -x

echo "🚀 Setting up SpotifyTool server..."

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "❌ Error: pipx is not installed."
    echo "Please install pipx first:"
    echo "  brew install pipx"
    echo "  pipx ensurepath"
    exit 1
fi

# Install package using pipx
echo "📦 Installing SpotifyTool package..."
if pipx list | grep -q "spotifytool"; then
    pipx reinstall spotifytool
else
    pipx install -e .
fi

# Create launch agent plist file
echo "📝 Creating launch agent..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.surya.spotifytool-server.plist"

echo "HOME is: $HOME"
echo "PLIST_PATH is: $PLIST_PATH"
whoami
touch "$PLIST_PATH" && echo "Touch succeeded" || echo "Touch failed"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>EnvironmentVariables</key>
    <dict>
    <key>PATH</key>
    <string>/Users/surya/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>Label</key>
    <string>com.surya.spotifytool-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/surya/.local/bin/spotifytool-server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/spotifytool-server.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/spotifytool-server.log</string>
</dict>
</plist>
EOF

# Unload the launch agent if it already exists
echo "🔄 Configuring launch agent..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load the launch agent
launchctl load "$PLIST_PATH"

# Wait a moment for the server to start
echo "⏳ Starting server..."
sleep 2

# Verify server is running
echo "🔍 Checking server status..."
if curl -s http://127.0.0.1:5000/health | grep -q "online"; then
    echo "✅ SpotifyTool server is running successfully!"
    echo "   You can view logs at: /tmp/spotifytool-server.log"
    echo "   Error logs are at: /tmp/spotifytool-server.err"
else
    echo "❌ Server not responding. Please check /tmp/spotifytool-server.log for errors."
fi

echo ""
echo "Next steps:"
echo "1. Reload your Chrome extension at chrome://extensions"
echo "2. Make sure host_permissions are set correctly in manifest.json"
echo "3. Try downloading a YouTube or SoundCloud track through the extension"

chmod +x setup_server.sh