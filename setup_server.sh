#!/bin/bash
# filepath: /Users/surya/Developer/yt2mp3/setup_server.sh

set -e  # Exit on error

echo "🚀 Setting up YT2MP3 server..."

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "❌ Error: pipx is not installed."
    echo "Please install pipx first:"
    echo "  brew install pipx"
    echo "  pipx ensurepath"
    exit 1
fi

# Install package using pipx
echo "📦 Installing YT2MP3 package..."
if pipx list | grep -q "yt2mp3"; then
    pipx reinstall .
else
    pipx install -e .
fi

# Create launch agent plist file
echo "📝 Creating launch agent..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.surya.yt2mp3-server.plist"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.surya.yt2mp3-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>yt2mp3-server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/yt2mp3-server.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/yt2mp3-server.log</string>
</dict>
</plist>
EOF

# Unload the launch agent if it already exists
echo "🔄 Configuring launch agent..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load the launch agent
launchctl load "$PLIST_PATH"

# Remove old native messaging configuration if it exists
NATIVE_MSG_PATH="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.surya.yt2mp3.json"
if [ -f "$NATIVE_MSG_PATH" ]; then
    echo "🧹 Removing old native messaging configuration..."
    rm "$NATIVE_MSG_PATH"
fi

# Wait a moment for the server to start
echo "⏳ Starting server..."
sleep 2

# Verify server is running
echo "🔍 Checking server status..."
if curl -s http://127.0.0.1:5000/health | grep -q "online"; then
    echo "✅ YT2MP3 server is running successfully!"
    echo "   You can view logs at: /tmp/yt2mp3-server.log"
    echo "   Error logs are at: /tmp/yt2mp3-server.err"
else
    echo "❌ Server not responding. Please check /tmp/yt2mp3-server.log for errors."
fi

echo ""
echo "Next steps:"
echo "1. Reload your Chrome extension at chrome://extensions"
echo "2. Make sure host_permissions are set correctly in manifest.json"
echo "3. Try downloading a YouTube video through the extension"

chmod +x setup_server.sh