// Track active downloads
let activeDownloads = new Map(); // downloadId -> {url, title, status, startTime}
let notificationsSent = new Set(); // Track which downloads already got notifications

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'openPopup') {
    chrome.action.openPopup();
    return;
  }

  if (request.action === 'getActiveDownloads') {
    sendResponse({ downloads: Array.from(activeDownloads.values()) });
    return;
  }

  if (request.action === 'download') {
    const { url, title } = request;
    const downloadId = Date.now() + Math.random(); // Unique ID
    
    // Validate URL
    try {
      new URL(url);
    } catch (e) {
      sendResponse({ error: 'Invalid URL' });
      return true;
    }

    // Extract a better title from URL if no title provided
    const extractTitleFromUrl = (url) => {
      try {
        const urlObj = new URL(url);
        if (url.includes('youtube.com')) {
          return `YouTube Video (${urlObj.searchParams.get('v') || 'Unknown'})`;
        } else if (url.includes('soundcloud.com')) {
          const pathParts = urlObj.pathname.split('/').filter(p => p);
          return pathParts.length >= 2 ? `${pathParts[pathParts.length-1].replace(/-/g, ' ')}` : 'SoundCloud Track';
        }
        return 'Unknown Track';
      } catch {
        return 'Unknown Track';
      }
    };

    // Track this download
    const downloadInfo = {
      id: downloadId,
      url: url,
      title: title || extractTitleFromUrl(url),
      status: 'downloading',
      startTime: Date.now(),
      platform: url.includes('soundcloud.com') ? 'SoundCloud' : 'YouTube'
    };
    activeDownloads.set(downloadId, downloadInfo);

    // Update badge to show active download count
    chrome.action.setBadgeText({ text: activeDownloads.size.toString() });
    chrome.action.setBadgeBackgroundColor({ color: '#FF6B35' });

    // Send to server
    console.log('Sending download request:', { url, title });
    fetch('http://127.0.0.1:5000/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url, title }),
    })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.text(); // Get text first to debug
    })
    .then(text => {
      console.log('Raw response text:', text);
      try {
        return JSON.parse(text);
      } catch (e) {
        console.error('JSON parse error:', e);
        console.error('Response text was:', text);
        throw new Error('Invalid JSON response from server');
      }
    })
    .then(data => {
      // Update download status
      const download = activeDownloads.get(downloadId);
      if (download) {
        if (data.status === 'success') {
          download.status = 'completed';
          download.message = data.message;
          
          // Show notification and pop up only once
          if (!notificationsSent.has(downloadId)) {
            notificationsSent.add(downloadId);
            
            chrome.notifications.create({
              type: 'basic',
              iconUrl: 'assets/crocodile.png',
              title: 'Download Complete! 🎵',
              message: `${download.title} from ${download.platform}`
            });
            
            // Pop up the extension
            chrome.action.openPopup();
          }
          
          sendResponse({ success: true, message: data.message, downloadId });
        } else {
          download.status = 'failed';
          download.error = data.reason;
          
          // Show error notification only once
          if (!notificationsSent.has(downloadId)) {
            notificationsSent.add(downloadId);
            
            chrome.notifications.create({
              type: 'basic',
              iconUrl: 'assets/crocodile.png',
              title: 'Download Failed ❌',
              message: `${download.title}: ${data.reason}`
            });
          }
          
          sendResponse({ error: data.reason || 'Server error', downloadId });
        }
        
        // Remove completed/failed downloads after 5 seconds
        setTimeout(() => {
          activeDownloads.delete(downloadId);
          notificationsSent.delete(downloadId); // Clean up notification tracking
          const remaining = activeDownloads.size;
          if (remaining === 0) {
            chrome.action.setBadgeText({ text: '' });
          } else {
            chrome.action.setBadgeText({ text: remaining.toString() });
          }
        }, 5000);
      }
    })
    .catch(error => {
      const download = activeDownloads.get(downloadId);
      if (download) {
        download.status = 'failed';
        download.error = error.message;
        
        if (!notificationsSent.has(downloadId)) {
          notificationsSent.add(downloadId);
          
          chrome.notifications.create({
            type: 'basic',
            iconUrl: 'assets/crocodile.png',
            title: 'Connection Error ❌',
            message: `Failed to connect to server`
          });
        }
        
        setTimeout(() => {
          activeDownloads.delete(downloadId);
          notificationsSent.delete(downloadId);
          const remaining = activeDownloads.size;
          chrome.action.setBadgeText({ text: remaining === 0 ? '' : remaining.toString() });
        }, 5000);
      }
      sendResponse({ error: error.message || 'Could not connect to server', downloadId });
    });

    return true; // Keep the message channel open for async response
  }
});


