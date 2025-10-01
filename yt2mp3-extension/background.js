chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'openPopup') {
    chrome.action.openPopup();
    return;
  }

  if (request.action === 'download') {
    const { url, title } = request;
    
    // Validate URL
    try {
      new URL(url);
    } catch (e) {
      sendResponse({ error: 'Invalid URL' });
      return true;
    }

    // Send to server instead of native messaging
    fetch('http://127.0.0.1:5000/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url, title }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        sendResponse({ success: true });
      } else {
        sendResponse({ error: data.reason || 'Server error' });
      }
    })
    .catch(error => {
      sendResponse({ error: error.message || 'Could not connect to server' });
    });

    return true; // Keep the message channel open for async response
  }
});


