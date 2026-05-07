(function (window, document) {
  "use strict";

  const DISMISS_KEY = "pvl_install_prompt_dismissed_v1";
  let deferredInstallPromptEvent = null;

  function isIos() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent || "");
  }

  function isSafari() {
    const ua = window.navigator.userAgent || "";
    return /safari/i.test(ua) && !/crios|fxios|edgios|opios|mercury/i.test(ua);
  }

  function isAndroid() {
    return /android/i.test(window.navigator.userAgent || "");
  }

  function isStandalone() {
    const iosStandalone = window.navigator.standalone === true;
    const mediaStandalone =
      window.matchMedia &&
      window.matchMedia("(display-mode: standalone)").matches;
    return iosStandalone || mediaStandalone;
  }

  function applyStandaloneClass() {
    const standalone = isStandalone();
    document.documentElement.classList.toggle("pwa-standalone", standalone);
    document.documentElement.classList.toggle("pwa-browser", !standalone);
    return standalone;
  }

  function isDismissed() {
    try {
      return window.localStorage.getItem(DISMISS_KEY) === "1";
    } catch (_err) {
      return false;
    }
  }

  function markDismissed() {
    try {
      window.localStorage.setItem(DISMISS_KEY, "1");
    } catch (_err) {}
  }

  function clearDismissed() {
    try {
      window.localStorage.removeItem(DISMISS_KEY);
    } catch (_err) {}
  }

  function shouldShowIosPrompt() {
    return isIos() && isSafari() && !isStandalone() && !isDismissed();
  }

  function shouldShowAndroidPrompt() {
    return isAndroid() && !isStandalone() && !isDismissed() && !!deferredInstallPromptEvent;
  }

  function shouldShowInstallPrompt() {
    return shouldShowIosPrompt() || shouldShowAndroidPrompt();
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in window.navigator)) return Promise.resolve(null);
    if (!window.isSecureContext) return Promise.resolve(null);

    return window.navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch(function () {
        return null;
      });
  }

  function promptAndroidInstall() {
    if (!deferredInstallPromptEvent) return Promise.resolve(false);
    deferredInstallPromptEvent.prompt();
    return deferredInstallPromptEvent.userChoice
      .then(function (choice) {
        deferredInstallPromptEvent = null;
        return choice && choice.outcome === "accepted";
      })
      .catch(function () {
        return false;
      });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPromptEvent = event;
    window.dispatchEvent(new CustomEvent("pvl:android-install-ready"));
  });

  window.addEventListener("appinstalled", function () {
    clearDismissed();
    applyStandaloneClass();
  });

  window.PVLPwaInstall = {
    isIos: isIos,
    isSafari: isSafari,
    isAndroid: isAndroid,
    isStandalone: isStandalone,
    applyStandaloneClass: applyStandaloneClass,
    shouldShowInstallPrompt: shouldShowInstallPrompt,
    shouldShowIosPrompt: shouldShowIosPrompt,
    shouldShowAndroidPrompt: shouldShowAndroidPrompt,
    markDismissed: markDismissed,
    clearDismissed: clearDismissed,
    registerServiceWorker: registerServiceWorker,
    promptAndroidInstall: promptAndroidInstall
  };
})(window, document);
