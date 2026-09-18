(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var lastFocusedEl = null;

  function getFocusable(container) {
    return Array.prototype.slice.call(
      container.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter(function (el) { return el.offsetParent !== null; });
  }

  function trapFocus(container, e) {
    if (e.key !== 'Tab') return;
    var focusable = getFocusable(container);
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  /* ---------------- Header scroll state ---------------- */
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () {
      header.classList.toggle('is-scrolled', window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------------- Mobile nav overlay ---------------- */
  var hamburger = document.querySelector('[data-nav-toggle]');
  var overlay = document.querySelector('[data-nav-overlay]');
  var navClose = document.querySelector('[data-nav-close]');

  function openNav() {
    if (!overlay) return;
    lastFocusedEl = document.activeElement;
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    overlay.setAttribute('aria-hidden', 'false');
    hamburger && hamburger.setAttribute('aria-expanded', 'true');
    var focusable = getFocusable(overlay);
    if (focusable.length) focusable[0].focus();
  }
  function closeNav() {
    if (!overlay || !overlay.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
    overlay.setAttribute('aria-hidden', 'true');
    hamburger && hamburger.setAttribute('aria-expanded', 'false');
    if (lastFocusedEl) lastFocusedEl.focus();
  }
  if (hamburger) hamburger.addEventListener('click', openNav);
  if (navClose) navClose.addEventListener('click', closeNav);
  if (overlay) {
    overlay.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeNav);
    });
    overlay.addEventListener('keydown', function (e) { trapFocus(overlay, e); });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeNav();
      closeModal();
    }
  });

  /* ---------------- FAQ accordion ---------------- */
  document.querySelectorAll('.faq-item').forEach(function (item) {
    var btn = item.querySelector('.faq-question');
    var answer = item.querySelector('.faq-answer');
    if (!btn || !answer) return;
    btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('click', function () {
      var isOpen = item.classList.contains('is-open');
      document.querySelectorAll('.faq-item.is-open').forEach(function (openItem) {
        if (openItem !== item) {
          openItem.classList.remove('is-open');
          openItem.querySelector('.faq-answer').style.maxHeight = null;
          openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        }
      });
      if (isOpen) {
        item.classList.remove('is-open');
        answer.style.maxHeight = null;
        btn.setAttribute('aria-expanded', 'false');
      } else {
        item.classList.add('is-open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  /* ---------------- Reveal on scroll ---------------- */
  var revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    if (prefersReducedMotion || !('IntersectionObserver' in window)) {
      revealEls.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
      var groups = {};
      revealEls.forEach(function (el) {
        var group = el.getAttribute('data-reveal-group') || 'default';
        groups[group] = groups[group] || [];
        groups[group].push(el);
      });
      Object.keys(groups).forEach(function (key) {
        groups[key].forEach(function (el, i) {
          el.style.transitionDelay = (i * 80) + 'ms';
        });
      });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      revealEls.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------------- WhatsApp deep links ----------------
     Static links are rendered server-side (see wa_url() in build.py) — only
     the booking form still needs to build one at submit time, from the
     values the visitor just typed. */
  var body = document.body;
  var waNumber = body.getAttribute('data-whatsapp-number');

  function buildWhatsappUrl(message) {
    return 'https://wa.me/' + waNumber + '?text=' + encodeURIComponent(message);
  }

  /* ---------------- Booking modal ---------------- */
  var modalBackdrop = document.querySelector('[data-booking-modal]');
  var modalOpenTriggers = document.querySelectorAll('[data-open-booking]');
  var modalCloseTriggers = document.querySelectorAll('[data-close-booking]');
  var bookingForm = document.querySelector('[data-booking-form]');
  var modalPanel = modalBackdrop ? modalBackdrop.querySelector('.modal-panel') : null;
  var presetDoctor = '';

  function openModal(presetService, presetDoctorName) {
    if (!modalBackdrop) return;
    lastFocusedEl = document.activeElement;
    presetDoctor = presetDoctorName || '';
    modalBackdrop.classList.add('is-open');
    modalBackdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (presetService && bookingForm) {
      var select = bookingForm.querySelector('[name="service"]');
      if (select) select.value = presetService;
    }
    if (bookingForm) {
      var nameInput = bookingForm.querySelector('[name="name"]');
      if (nameInput) nameInput.focus();
    }
  }
  function closeModal() {
    if (!modalBackdrop || !modalBackdrop.classList.contains('is-open')) return;
    modalBackdrop.classList.remove('is-open');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lastFocusedEl) lastFocusedEl.focus();
  }
  modalOpenTriggers.forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      openModal(el.getAttribute('data-service'), el.getAttribute('data-doctor'));
    });
  });
  modalCloseTriggers.forEach(function (el) { el.addEventListener('click', closeModal); });
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', function (e) {
      if (e.target === modalBackdrop) closeModal();
    });
  }
  if (modalPanel) {
    modalPanel.addEventListener('keydown', function (e) { trapFocus(modalPanel, e); });
  }

  if (bookingForm) {
    var tmpl = bookingForm.getAttribute('data-message-template') || '';
    bookingForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = bookingForm.querySelector('[name="name"]').value.trim();
      var phone = bookingForm.querySelector('[name="phone"]').value.trim();
      var service = bookingForm.querySelector('[name="service"]').value;
      var contact = bookingForm.querySelector('[name="contactMethod"]').value;
      var msg = bookingForm.querySelector('[name="message"]').value.trim();

      var serviceClause = service ? bookingForm.getAttribute('data-service-clause').replace('{service}', service) : '';
      var doctorClause = presetDoctor ? bookingForm.getAttribute('data-doctor-clause').replace('{doctor}', presetDoctor) : '';
      var messageClause = msg ? bookingForm.getAttribute('data-message-clause').replace('{message}', msg) : '';

      var finalMessage = tmpl
        .replace('{name}', name || '—')
        .replace('{phone}', phone || '—')
        .replace('{doctorClause}', doctorClause)
        .replace('{serviceClause}', serviceClause)
        .replace('{contact}', contact)
        .replace('{messageClause}', messageClause);

      window.open(buildWhatsappUrl(finalMessage), '_blank', 'noopener');
      closeModal();
      bookingForm.reset();
    });
  }
})();
