(() => {
  // SoundCloud-specific injection for track pages
  const BUTTON_CLASS = 'spotify-tool-soundcloud-button';
  const BUTTON_TITLE = 'Download with Spotify Tool';

  function createSoundCloudButtonElement() {
    const btn = document.createElement('button');
    btn.className = 'sc-button-repost sc-button-secondary sc-button sc-button-medium sc-button-icon sc-button-responsive ' + BUTTON_CLASS;
    btn.title = 'download';
    btn.setAttribute('aria-label', BUTTON_TITLE);
    btn.setAttribute('tabindex', '0');

    const img = document.createElement('img');
    try {
      img.src = chrome.runtime.getURL('assets/peace.png');
    } catch (err) {
      console.warn('chrome.runtime.getURL unavailable; using relative path fallback', err);
      img.src = '/assets/peace.png';
    }
    img.alt = 'Download';
    img.style.width = '16px';
    img.style.height = '16px';
    img.style.objectFit = 'contain';
    img.style.display = 'block';
    
    btn.appendChild(img);
    return btn;
  }

  function addSoundCloudButtonIfNeeded() {
    try {
      const existing = document.querySelector('.' + BUTTON_CLASS);
      if (existing) return;

      // Look for SoundCloud button group
      const buttonGroup = document.querySelector('.sc-button-group');
      if (!buttonGroup) return; // not ready yet

      // Only add if we're on a track page (has play button)
      const playButton = document.querySelector('.playButton, .sc-button-play, [title*="Play"]');
      if (!playButton) return; // not a track page

      const btn = createSoundCloudButtonElement();

      // Add to button group
      buttonGroup.appendChild(btn);
      
      console.log('SoundCloud Spotify Tool button added');
    } catch (err) {
      console.error('Error adding SoundCloud Spotify Tool button', err);
    }
  }

  function waitForSoundCloudElements() {
    const maxAttempts = 50; // Try for up to 10 seconds
    let attempts = 0;

    const checkForElements = () => {
      attempts++;
      const buttonGroup = document.querySelector('.sc-button-group');
      const playButton = document.querySelector('.playButton, .sc-button-play, [title*="Play"]');
      
      if (buttonGroup && playButton) {
        addSoundCloudButtonIfNeeded();
        return true;
      } else if (attempts < maxAttempts) {
        setTimeout(checkForElements, 200); // Check every 200ms
        return false;
      }
      return false;
    };

    checkForElements();
  }

  // Delegate click handling for SoundCloud button
  document.addEventListener('click', (ev) => {
    const target = ev.target instanceof Element ? ev.target.closest('.' + BUTTON_CLASS) : null;
    if (!target) return;

    // Prevent default SoundCloud behavior
    ev.preventDefault();
    ev.stopPropagation();

    // Try to message the background service worker
    try {
      if (chrome && chrome.runtime && typeof chrome.runtime.sendMessage === 'function') {
        chrome.runtime.sendMessage({ action: 'openPopup' }, (resp) => {
          // optional callback handling
        });
      } else {
        console.error('chrome.runtime.sendMessage is not available in this context');
      }
    } catch (err) {
      console.error('Failed to send message to background', err);
    }
  });

  // Observe the page for changes (SoundCloud is a single-page app)
  const observer = new MutationObserver((mutations) => {
    // Check if this is a navigation change or button group update
    const hasRelevantChanges = mutations.some(mutation => 
      Array.from(mutation.addedNodes).some(node => 
        node.nodeType === 1 && (
          node.matches && (
            node.matches('.sc-button-group') ||
            node.matches('.playButton') ||
            node.querySelector && (
              node.querySelector('.sc-button-group') ||
              node.querySelector('.playButton')
            )
          )
        )
      )
    );
    
    if (hasRelevantChanges) {
      // Delay slightly to let SoundCloud finish setting up
      setTimeout(addSoundCloudButtonIfNeeded, 100);
    }
    
    addSoundCloudButtonIfNeeded();
  });

  observer.observe(document.documentElement || document.body, { 
    childList: true, 
    subtree: true 
  });

  // Listen for SoundCloud navigation events (if they exist)
  window.addEventListener('popstate', () => {
    setTimeout(() => {
      waitForSoundCloudElements();
    }, 500);
  });

  // Initial attempts
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      waitForSoundCloudElements();
    });
  } else {
    waitForSoundCloudElements();
  }

  window.addEventListener('load', () => {
    addSoundCloudButtonIfNeeded();
    waitForSoundCloudElements();
  });

  // Also try when URL changes (for SoundCloud's SPA navigation)
  let lastUrl = location.href;
  new MutationObserver(() => {
    const currentUrl = location.href;
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl;
      // When URL changes, wait for the new track to load
      setTimeout(() => {
        waitForSoundCloudElements();
        addSoundCloudButtonIfNeeded();
      }, 1000); // Longer delay for SoundCloud
    }
  }).observe(document, { subtree: true, childList: true });
})();