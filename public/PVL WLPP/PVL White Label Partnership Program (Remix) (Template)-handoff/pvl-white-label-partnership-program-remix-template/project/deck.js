/* PVL White Label deck — interactions */

(() => {
  const stage = document.querySelector('deck-stage');
  if (!stage) return;

  const slideOnceSetup = {};
  const slideEverySetup = {};
  const revealedOnce = new Set();
  const slides = Array.from(stage.querySelectorAll(':scope > section'));

  function revealSlide(slide) {
    if (!slide) return;
    slide.classList.add('reveal');
    if (!revealedOnce.has(slide.id)) {
      revealedOnce.add(slide.id);
      slideOnceSetup[slide.id]?.(slide);
    }
    slideEverySetup[slide.id]?.(slide);
  }

  // Primary trigger: slidechange event
  stage.addEventListener('slidechange', (e) => revealSlide(e.detail?.slide));

  // Fallback 1: MutationObserver on each slide watching data-deck-active
  const mo = new MutationObserver((muts) => {
    for (const m of muts) {
      const t = m.target;
      if (t.hasAttribute && t.hasAttribute('data-deck-active')) revealSlide(t);
    }
  });
  slides.forEach(s => mo.observe(s, { attributes: true, attributeFilter: ['data-deck-active'] }));

  // Fallback 2: on load, reveal whatever's currently active
  function revealActive() {
    const active = slides.find(s => s.hasAttribute('data-deck-active'));
    if (active) revealSlide(active);
    else revealSlide(slides[0]);
  }
  requestAnimationFrame(revealActive);
  setTimeout(revealActive, 200);

  function easeOutCubic(t){ return 1 - Math.pow(1 - t, 3); }
  function formatNum(n, target) {
    if (target >= 1000) return n.toLocaleString('en-US', { maximumFractionDigits: 0 });
    return Math.round(n).toString();
  }
  function runCounter(el) {
    const target = +el.dataset.target;
    const suffix = el.dataset.suffix || '';
    const dur = 1400;
    const start = performance.now();
    function tick(now) {
      const t = Math.min(1, (now - start) / dur);
      const v = target * easeOutCubic(t);
      el.textContent = formatNum(v, target) + (t === 1 ? suffix : (suffix && t > 0.99 ? suffix : ''));
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = formatNum(target, target) + suffix;
    }
    requestAnimationFrame(tick);
  }
  slideEverySetup['slide-1'] = (slide) => {
    // reset & re-run counters each time slide becomes active
    slide.querySelectorAll('.counter').forEach(el => {
      el.textContent = '0';
      // small delay so it lines up with the fade-up
      setTimeout(() => runCounter(el), 700);
    });
  };

  // ----------------------------------------------------------
  // Slide 3: packaging tab expand
  // ----------------------------------------------------------
  slideOnceSetup['slide-3'] = (slide) => {
    const tabs = slide.querySelectorAll('.s3-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.setAttribute('aria-expanded', t === tab ? 'true' : 'false'));
      });
      tab.addEventListener('mouseenter', () => {
        tabs.forEach(t => t.setAttribute('aria-expanded', t === tab ? 'true' : 'false'));
      });
    });
  };

  // ----------------------------------------------------------
  // Slide 5: interactive volume / pricing calculator
  // ----------------------------------------------------------
  slideOnceSetup['slide-6'] = (slide) => {
    const slider = slide.querySelector('#volSlider');
    const tableRows = Array.from(slide.querySelectorAll('#pricingTable .s5-tr[data-price]'));
    const qtyOut    = slide.querySelector('#calcQty');
    const unitOut   = slide.querySelector('#calcUnitPrice');
    const boxOut    = slide.querySelector('#calcBoxPrice');
    const prodOut   = slide.querySelector('#calcProduct');
    const boxesOut  = slide.querySelector('#calcBoxes');
    const totOut    = slide.querySelector('#calcTotal');
    const revOut    = slide.querySelector('#calcRev');

    const RETAIL = 29.99;
    const fmt$ = (n) => '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
    const fmtN = (n) => n.toLocaleString('en-US');

    function unitPrice(q) {
      if (q < 2500) return 10;
      if (q < 5000) return 9;
      if (q < 10000) return 8;
      if (q < 25000) return 7;
      return 6;
    }
    function boxPrice(q) {
      if (q < 5000) return 0.50;
      if (q < 10000) return 0.35;
      return 0.20;
    }
    function pctProgress(v){
      const min = +slider.min, max = +slider.max;
      return ((v - min) / (max - min)) * 100;
    }

    function update() {
      const q = +slider.value;
      const up = unitPrice(q);
      const bp = boxPrice(q);
      const product = q * up;
      const boxes = q * bp;
      const total = product + boxes;
      const revenue = q * RETAIL;

      qtyOut.textContent  = fmtN(q);
      unitOut.textContent = '$' + up.toFixed(2);
      boxOut.textContent  = '$' + bp.toFixed(2);
      prodOut.textContent = fmt$(product);
      boxesOut.textContent= fmt$(boxes);
      totOut.textContent  = fmt$(total);
      revOut.textContent  = '~' + fmt$(revenue);

      slider.style.setProperty('--prog', pctProgress(q) + '%');

      tableRows.forEach(r => {
        const mn = +r.dataset.min, mx = +r.dataset.max;
        r.classList.toggle('active', q >= mn && q <= mx);
      });
    }
    slider.addEventListener('input', update);
    update();
  };
  slideEverySetup['slide-6'] = (slide) => {
    const slider = slide.querySelector('#volSlider');
    if (slider) slider.dispatchEvent(new Event('input'));
  };

  // ----------------------------------------------------------
  // Slide 6: CTA actions (placeholders — clients can wire up)
  // ----------------------------------------------------------
  slideOnceSetup['slide-6'] = (slide) => {
    const btn = slide.querySelector('[data-action="proposal"]');
    btn?.addEventListener('click', () => {
      window.location.href = 'mailto:dane@provibelife.com?subject=White%20Label%20Partnership%20Inquiry&body=Hi%20Dane%2C%0A%0AI%27d%20like%20to%20learn%20more%20about%20the%20Pro%20Vibe%20Life%20white%20label%20program.%0A%0AVolume%20I%27m%20considering%3A%20%0APackaging%20option%3A%20%0ATimeline%3A%20%0A%0AThanks!';
    });
  };
})();
