(() => {
  const injectButton = () => {
    const buttonClassName = "yt2mp3-button";
    let youtubeRightControls, youtubePlayer;
    const buttonTitle = "Yt2MP3 Download";
    const toolTipMessage = "Add ts video to spotify 🥹.";
    const downloadBtnExists = document.getElementsByClassName(buttonClassName)[0];

    if (!downloadBtnExists) {
      const btn = document.createElement("button");
      btn.className = "ytp-button " + buttonClassName;
      btn.title = buttonTitle;
      btn.setAttribute("aria-label", buttonTitle);
      btn.setAttribute("data-title-no-tooltip", toolTipMessage);

      const img = document.createElement("img");
      img.src = chrome.runtime.getURL("assets/peace.png");
      img.alt = buttonTitle;
      img.style.width = "24px";
      img.style.height = "24px";
      img.style.objectFit = "contain";
      img.style.display = "block";
      img.style.margin = "0 auto";
      btn.appendChild(img);

      // Set up handlers
      let tooltipShowTimeout;
      btn.addEventListener('mouseenter', () => {
        clearTimeout(tooltipShowTimeout);
        // Find the existing tooltip and text span
        const tooltip = document.querySelector('.ytp-tooltip.ytp-bottom');
        const tooltipText = tooltip ? tooltip.querySelector('.ytp-tooltip-text') : null;
        const tooltipBg = tooltip ? tooltip.querySelector('.ytp-tooltip-bg') : null;
        if (tooltip && tooltipText) {
          tooltipShowTimeout = setTimeout(() => {
            tooltip.classList.remove('ytp-preview');
            tooltipText.textContent = toolTipMessage;
            tooltip.style.removeProperty('display');
            tooltip.style.maxWidth = '300px';

            if (tooltipBg) {
              tooltipBg.style.removeProperty('background');
            }

            const btnRect = btn.getBoundingClientRect();
            const playerRect = btn.closest('.html5-video-player').getBoundingClientRect();
            // Calculate left so the tooltip is centered above the button
            const tooltipWidth = tooltip.offsetWidth || 120; // fallback width
            const left = btnRect.left - playerRect.left + (btnRect.width / 2) - (tooltipWidth / 2);

            tooltip.style.left = `${left}px`;
            tooltip.style.top = `calc(${btnRect.top - playerRect.top - tooltip.offsetHeight}px - 12px)`;
          }, 100);
        }
      });

      btn.addEventListener('mouseleave', () => {
        const tooltip = document.querySelector('.ytp-tooltip.ytp-bottom');
        const tooltipText = tooltip ? tooltip.querySelector('.ytp-tooltip-text') : null;
        if (tooltip && tooltipText && tooltipText.textContent === toolTipMessage) {
          tooltip.style.display = 'none';
        }
      });

      // Handle click event
      btn.addEventListener("click", () => chrome.runtime.sendMessage({ action: 'openPopup' }));

      youtubeRightControls = document.getElementsByClassName("ytp-right-controls")[0];
      youtubePlayer = document.getElementsByClassName("video-stream")[0];

      youtubeRightControls.prepend(btn);
    }
  }

  chrome.runtime.onMessage.addListener((obj, sender, response) => {
    const { type, value, videoId } = obj;

    if (type === "NEW") {
      currentVideo = videoId;
      injectButton();
    }
  });

  injectButton();
})();