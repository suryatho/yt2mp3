document.addEventListener('DOMContentLoaded', () => {
  const titleInput = document.getElementById('title');
  const downloadBtn = document.getElementById('download');
  const statusEl = document.getElementById('status');

  downloadBtn.addEventListener('click', async () => {
    // Get the active tab's URL (for YouTube)
    let videoUrl = null;
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url && tab.url.includes('youtube.com/watch')) {
        videoUrl = tab.url;
      }
    } catch (e) {
      // fallback: do nothing, videoUrl stays null
    }

    const title = titleInput.value.trim();
    const titleToSend = title ? title : null;

    // Show loading state
    statusEl.classList.remove('hidden');
    statusEl.textContent = "Starting download...";
    downloadBtn.disabled = true;

    try {
      // Send to background script
      const response = await chrome.runtime.sendMessage({
        action: 'download',
        url: videoUrl,
        title: titleToSend
      });

      if (response.error) {
        throw new Error(response.error);
      }

      // Success
      statusEl.textContent = "Done! ✅";
    } catch (error) {
      statusEl.textContent = `Error ❌: ${error.message}`;
      downloadBtn.disabled = false;
    }
  });

  // Close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') window.close();
  });
});