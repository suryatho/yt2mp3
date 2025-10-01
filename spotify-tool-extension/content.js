(() => {
  // Robust injection for YouTube's dynamic DOM. Waits for controls to appear,
  // re-injects on navigation, and delegates click handling so chrome.runtime
  // is only referenced at click time (avoids "context undefined" errors).

  const BUTTON_CLASS = 'spotify-tool-button';
  const BUTTON_TITLE = 'Add to Spotify';
  const TOOLTIP_MSG = 'Add this track to Spotify ✌️';

  function createButtonElement() {
    const btn = document.createElement('button');
    btn.className = 'ytp-button ' + BUTTON_CLASS;
    btn.title = BUTTON_TITLE;
    btn.setAttribute('aria-label', BUTTON_TITLE);
    btn.setAttribute('data-title-no-tooltip', TOOLTIP_MSG);

    const img = document.createElement('img');
    try {
      img.src = chrome.runtime.getURL('assets/peace.png');
    } catch (err) {
      // chrome.runtime may be undefined in some contexts while evaluating; use a safe fallback
      console.warn('chrome.runtime.getURL unavailable; using relative path fallback', err);
      img.src = '/assets/peace.png';
    }
    img.alt = BUTTON_TITLE;
    img.style.width = '24px';
    img.style.height = '24px';
    img.style.objectFit = 'contain';
    img.style.display = 'block';
    img.style.margin = '0 auto';
    btn.appendChild(img);

    // Tooltip behavior (best-effort)
    let tooltipShowTimeout;
    btn.addEventListener('mouseenter', () => {
      clearTimeout(tooltipShowTimeout);
      const tooltip = document.querySelector('.ytp-tooltip.ytp-bottom');
      const tooltipText = tooltip ? tooltip.querySelector('.ytp-tooltip-text') : null;
      const tooltipBg = tooltip ? tooltip.querySelector('.ytp-tooltip-bg') : null;
      if (tooltip && tooltipText) {
        tooltipShowTimeout = setTimeout(() => {
          tooltip.classList.remove('ytp-preview');
          tooltipText.textContent = TOOLTIP_MSG;
          tooltip.style.removeProperty('display');
          tooltip.style.maxWidth = '300px';
          if (tooltipBg) tooltipBg.style.removeProperty('background');
          const btnRect = btn.getBoundingClientRect();
          const player = btn.closest('.html5-video-player');
          const playerRect = player ? player.getBoundingClientRect() : { left: 0, top: 0 };
          const tooltipWidth = tooltip.offsetWidth || 120;
          const left = btnRect.left - playerRect.left + (btnRect.width / 2) - (tooltipWidth / 2);
          tooltip.style.left = `${left}px`;
          tooltip.style.top = `calc(${btnRect.top - playerRect.top - tooltip.offsetHeight}px - 12px)`;
        }, 100);
      }
    });
    btn.addEventListener('mouseleave', () => {
      const tooltip = document.querySelector('.ytp-tooltip.ytp-bottom');
      const tooltipText = tooltip ? tooltip.querySelector('.ytp-tooltip-text') : null;
      if (tooltip && tooltipText && tooltipText.textContent === TOOLTIP_MSG) tooltip.style.display = 'none';
    });

    return btn;
  }

  function addButtonIfNeeded() {
    try {
      const existing = document.querySelector('.' + BUTTON_CLASS);
      if (existing) return;

      const controls = document.querySelector('.ytp-right-controls');
      if (!controls) return; // not ready yet

      const btn = createButtonElement();

      // Use prepend to place it at the left of right-controls
      controls.prepend(btn);
    } catch (err) {
      console.error('Error adding Spotify Tool button', err);
    }
  }

  function waitForControlsAndInject() {
    const maxAttempts = 50; // Try for up to 10 seconds
    let attempts = 0;

    const checkForControls = () => {
      attempts++;
      const controls = document.querySelector('.ytp-right-controls');
      
      if (controls) {
        addButtonIfNeeded();
        return true;
      } else if (attempts < maxAttempts) {
        setTimeout(checkForControls, 200); // Check every 200ms
        return false;
      }
      return false;
    };

    checkForControls();
  }

  // Delegate click handling so we don't reference chrome.runtime during script evaluation
  document.addEventListener('click', (ev) => {
    const target = ev.target instanceof Element ? ev.target.closest('.' + BUTTON_CLASS) : null;
    if (!target) return;

    // Try to message the background service worker. If chrome.runtime isn't available
    // (very unlikely in a real content script), handle gracefully.
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

  // More aggressive button injection for YouTube's dynamic loading
  let injectionInterval;

  function startButtonInjection() {
    // Try to add button immediately
    addButtonIfNeeded();
    
    // Set up interval to keep trying (will stop once button is added)
    injectionInterval = setInterval(() => {
      const existing = document.querySelector('.' + BUTTON_CLASS);
      if (!existing) {
        addButtonIfNeeded();
      }
    }, 1000); // Check every second
  }

  function stopButtonInjection() {
    if (injectionInterval) {
      clearInterval(injectionInterval);
      injectionInterval = null;
    }
  }

  // Observe the page for changes (YouTube is a single-page app)
  const observer = new MutationObserver((mutations) => {
    // Check if this is a navigation change or player update
    const hasPlayerChanges = mutations.some(mutation => 
      Array.from(mutation.addedNodes).some(node => 
        node.nodeType === 1 && (
          node.matches && (
            node.matches('.html5-video-player') ||
            node.matches('.ytp-right-controls') ||
            node.querySelector && (
              node.querySelector('.html5-video-player') ||
              node.querySelector('.ytp-right-controls')
            )
          )
        )
      )
    );
    
    if (hasPlayerChanges) {
      // Delay slightly to let YouTube finish setting up
      setTimeout(addButtonIfNeeded, 100);
    }
    
    addButtonIfNeeded();
  });

  observer.observe(document.documentElement || document.body, { 
    childList: true, 
    subtree: true 
  });

  // Listen for YouTube navigation events
  window.addEventListener('yt-navigate-start', addButtonIfNeeded);
  window.addEventListener('yt-navigate-finish', addButtonIfNeeded);
  window.addEventListener('yt-page-data-updated', addButtonIfNeeded);

  // Initial attempts
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      startButtonInjection();
      waitForControlsAndInject();
    });
  } else {
    startButtonInjection();
    waitForControlsAndInject();
  }

  window.addEventListener('load', () => {
    addButtonIfNeeded();
    waitForControlsAndInject();
  });

  // Also try when URL changes (for YouTube's SPA navigation)
  let lastUrl = location.href;
  new MutationObserver(() => {
    const currentUrl = location.href;
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl;
      // When URL changes, wait for the new player to load
      setTimeout(() => {
        waitForControlsAndInject();
        addButtonIfNeeded();
      }, 500);
    }
  }).observe(document, { subtree: true, childList: true });
})();