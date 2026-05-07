(function (window, document) {
  "use strict";

  const PROMPT_ID = "pvl-ios-install-prompt";

  function removeExistingPrompt() {
    const existing = document.getElementById(PROMPT_ID);
    if (existing) existing.remove();
  }

  function buildPrompt() {
    const wrap = document.createElement("div");
    wrap.id = PROMPT_ID;
    wrap.className = "pvl-install-prompt";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-live", "polite");

    wrap.innerHTML = [
      '<div class="pvl-install-card">',
      '  <button type="button" class="pvl-install-close" aria-label="Dismiss install prompt">×</button>',
      '  <div class="pvl-install-title">Install Provibe Life</div>',
      '  <div class="pvl-install-copy">Tap Share and then Add to Home Screen for the best experience.</div>',
      '  <div class="pvl-install-actions">',
      '    <button type="button" class="btn sm ghost pvl-install-dismiss">Dismiss</button>',
      '    <button type="button" class="btn sm primary pvl-install-android">Install</button>',
      "  </div>",
      "</div>"
    ].join("");

    return wrap;
  }

  function mountPrompt() {
    if (!window.PVLPwaInstall) return;

    window.PVLPwaInstall.applyStandaloneClass();
    if (!window.PVLPwaInstall.shouldShowInstallPrompt()) {
      removeExistingPrompt();
      return;
    }

    removeExistingPrompt();
    const prompt = buildPrompt();
    document.body.appendChild(prompt);

    const androidBtn = prompt.querySelector(".pvl-install-android");
    if (!window.PVLPwaInstall.shouldShowAndroidPrompt()) {
      androidBtn.style.display = "none";
    }

    const dismiss = function () {
      window.PVLPwaInstall.markDismissed();
      prompt.classList.remove("is-visible");
      window.setTimeout(function () {
        prompt.remove();
      }, 220);
    };

    prompt.querySelector(".pvl-install-close").addEventListener("click", dismiss);
    prompt.querySelector(".pvl-install-dismiss").addEventListener("click", dismiss);

    androidBtn.addEventListener("click", function () {
      window.PVLPwaInstall.promptAndroidInstall().finally(dismiss);
    });

    window.requestAnimationFrame(function () {
      prompt.classList.add("is-visible");
    });
  }

  function init() {
    if (!window.PVLPwaInstall) return;
    window.PVLPwaInstall.registerServiceWorker().finally(mountPrompt);
    window.addEventListener("pvl:android-install-ready", mountPrompt);
  }

  window.PVLInstallPrompt = {
    init: init,
    mountPrompt: mountPrompt
  };
})(window, document);
