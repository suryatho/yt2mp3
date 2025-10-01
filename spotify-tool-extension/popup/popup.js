document.addEventListener('DOMContentLoaded', () => {
  const titleInput = document.getElementById('title');
  const downloadBtn = document.getElementById('download');
  const statusEl = document.getElementById('status');
  const downloadsListEl = document.getElementById('downloads-list');

  // Load and display active downloads when popup opens
  loadActiveDownloads();

  async function loadActiveDownloads() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getActiveDownloads' });
      displayDownloads(response.downloads);
    } catch (e) {
      console.error('Failed to load active downloads:', e);
    }
  }

  function displayDownloads(downloads) {
    if (!downloads || downloads.length === 0) {
      downloadsListEl.innerHTML = '';
      return;
    }

    downloadsListEl.innerHTML = downloads.map(dl => {
      const elapsed = Math.round((Date.now() - dl.startTime) / 1000);
      const statusIcon = dl.status === 'completed' ? '✅' : 
                        dl.status === 'failed' ? '❌' : '🔄';
      const statusText = dl.status === 'downloading' ? `${elapsed}s` : 
                        dl.status === 'completed' ? 'Done' : 'Failed';
      
      return `
        <div class="download-item ${dl.status}">
          <div class="download-info">
            <span class="download-title">${dl.title}</span>
            <span class="download-platform">${dl.platform}</span>
          </div>
          <div class="download-status">
            <span class="status-icon">${statusIcon}</span>
            <span class="status-text">${statusText}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // Refresh downloads list every second while popup is open (only if there are active downloads)
  const refreshInterval = setInterval(async () => {
    const response = await chrome.runtime.sendMessage({ action: 'getActiveDownloads' });
    const activeCount = response.downloads.filter(d => d.status === 'downloading').length;
    
    if (activeCount === 0) {
      // No active downloads, refresh less frequently
      setTimeout(loadActiveDownloads, 2000);
    } else {
      loadActiveDownloads();
    }
  }, 1000);

  // Clear interval when popup closes
  window.addEventListener('beforeunload', () => {
    clearInterval(refreshInterval);
  });

  downloadBtn.addEventListener('click', async () => {
    // Get the active tab's URL and extract page title
    let videoUrl = null;
    let pageTitle = null;
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        // Check if it's a supported platform
        if (tab.url.includes('youtube.com/watch') || 
            tab.url.includes('youtu.be/') || 
            tab.url.includes('soundcloud.com/')) {
          videoUrl = tab.url;
          
          // Extract title from the page
          try {
            const results = await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              func: () => {
                // Try YouTube selectors first
                let title = document.querySelector('h1.ytd-watch-metadata yt-formatted-string')?.textContent ||
                           document.querySelector('h1.style-scope.ytd-watch-metadata')?.textContent ||
                           document.querySelector('.watch-main-col h1')?.textContent;
                
                // If not YouTube, try SoundCloud selectors
                if (!title) {
                  title = document.querySelector('.trackItem__trackTitle')?.textContent ||
                         document.querySelector('.soundTitle__title')?.textContent ||
                         document.querySelector('h1[itemprop="name"]')?.textContent ||
                         document.querySelector('.sc-link-primary')?.textContent;
                }
                
                // Fallback to page title
                if (!title) {
                  title = document.title.replace(' - YouTube', '').replace(' | Free Listening on SoundCloud', '');
                }
                
                return title?.trim() || null;
              }
            });
            
            if (results && results[0] && results[0].result) {
              pageTitle = results[0].result;
            }
          } catch (scriptError) {
            console.warn('Could not extract page title:', scriptError);
          }
        }
      }
    } catch (e) {
      // fallback: do nothing, videoUrl stays null
    }

    const customTitle = titleInput.value.trim();
    // Use custom title if provided, otherwise use extracted page title, otherwise null
    const titleToSend = customTitle || pageTitle || null;

    // Validate URL
    if (!videoUrl) {
      statusEl.classList.remove('hidden');
      statusEl.textContent = "❌ No supported URL found. Please navigate to a YouTube or SoundCloud track.";
      return;
    }

    // Show loading state
    statusEl.classList.remove('hidden');
    statusEl.textContent = "🔄 Analyzing track...";
    downloadBtn.disabled = true;
    downloadBtn.textContent = "Processing...";

    try {
      console.log('Sending download request:', { url: videoUrl, title: titleToSend });
      
      // Send to background script
      const response = await chrome.runtime.sendMessage({
        action: 'download',
        url: videoUrl,
        title: titleToSend
      });
      
      console.log('Received response:', response);

      if (response.error) {
        throw new Error(response.error);
      }

      // Success - the server now waits for completion
      const successMsg = response.message || "Download completed! Check your Spotify folder.";
      statusEl.textContent = `✅ ${successMsg}`;
      statusEl.style.color = "#4CAF50";
      
      // Clear the title input for next download
      titleInput.value = '';
      
      // Don't auto-close - let user see the completed downloads list
      // The notification system will pop up the extension when downloads complete
      
    } catch (error) {
      console.error('Download error:', error);
      statusEl.textContent = `❌ Error: ${error.message}`;
      statusEl.style.color = "#f44336";
    } finally {
      downloadBtn.disabled = false;
      downloadBtn.textContent = "Add to Spotify 🎵";
    }
  });

  // Close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') window.close();
  });
});