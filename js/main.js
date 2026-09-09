/* =========================================================
   SecureSense — shared JS
   UI-only. No backend, no real auth, no real analysis.
   ========================================================= */

(function () {
  'use strict';

  var SESSION_KEY = 'securesense_user';

  /* ---------- Session helpers ---------- */

  function getUser() {
    try {
      var raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function setUser(user) {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
    } catch (e) {
      /* sessionStorage unavailable — navigation still works within a tab */
    }
  }

  function initials(name) {
    if (!name) return '?';
    var parts = name.trim().split(/\s+/);
    var chars = parts.slice(0, 2).map(function (p) { return p.charAt(0).toUpperCase(); });
    return chars.join('');
  }

  /* ---------- Login page ---------- */

  function initLoginPage() {
    var cards = document.querySelectorAll('[data-user-card]');
    cards.forEach(function (card) {
      card.addEventListener('click', function () {
        var user = {
          name: card.getAttribute('data-name'),
          phone: card.getAttribute('data-phone'),
          role: card.getAttribute('data-role') || 'Fraud Analyst'
        };
        setUser(user);
        window.location.href = 'dashboard.html';
      });
    });
  }

  /* ---------- Navbar (dashboard + call-check) ---------- */

  function initNavbar() {
    var nameEls = document.querySelectorAll('[data-navbar-name]');
    var avatarEls = document.querySelectorAll('[data-navbar-avatar]');
    var firstNameEls = document.querySelectorAll('[data-navbar-firstname]');
    if (!nameEls.length && !avatarEls.length && !firstNameEls.length) return;

    var user = getUser();
    if (!user) {
      // No demo user selected yet — send back to login.
      window.location.href = 'index.html';
      return;
    }

    nameEls.forEach(function (el) { el.textContent = user.name; });
    avatarEls.forEach(function (el) { el.textContent = initials(user.name); });
    firstNameEls.forEach(function (el) { el.textContent = user.name.split(' ')[0]; });
  }

  /* ---------- Nav pill tabs (call-check solution-style tabs, if present) ---------- */

  function initNavPills() {
    var pills = document.querySelectorAll('[data-pill-group] .nav-pill');
    if (!pills.length) return;
    pills.forEach(function (pill) {
      pill.addEventListener('click', function () {
        pills.forEach(function (p) { p.classList.remove('active'); });
        pill.classList.add('active');
      });
    });
  }

  /* ---------- Call Check: file upload UI ---------- */

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function initUploadZone() {
    var zone = document.querySelector('[data-upload-zone]');
    var input = document.querySelector('[data-upload-input]');
    var chip = document.querySelector('[data-file-chip]');
    var chipName = document.querySelector('[data-file-name]');
    var chipMeta = document.querySelector('[data-file-meta]');
    var removeBtn = document.querySelector('[data-file-remove]');
    var analyzeBtn = document.querySelector('[data-analyze-btn]');

    if (!zone || !input) return;

    function showFile(file) {
      if (!file) return;
      if (chipName) chipName.textContent = file.name;
      if (chipMeta) chipMeta.textContent = formatFileSize(file.size);
      if (chip) chip.classList.remove('hidden');
      if (analyzeBtn) analyzeBtn.disabled = false;
    }

    function clearFile() {
      input.value = '';
      if (chip) chip.classList.add('hidden');
      if (analyzeBtn) analyzeBtn.disabled = true;
      resetStages();
    }

    zone.addEventListener('click', function () {
      input.click();
    });

    zone.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        input.click();
      }
    });

    input.addEventListener('change', function () {
      if (input.files && input.files[0]) showFile(input.files[0]);
    });

    ['dragover', 'dragenter'].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        zone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'dragend', 'drop'].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        zone.classList.remove('is-dragover');
      });
    });

    zone.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files[0]) {
        input.files = files;
        showFile(files[0]);
      }
    });

    if (removeBtn) {
      removeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        clearFile();
      });
    }
  }

  /* ---------- Call Check: stage simulation (UI only) ---------- */

  var stageTimers = [];

  function resetStages() {
    stageTimers.forEach(function (t) { clearTimeout(t); });
    stageTimers = [];
    var stages = document.querySelectorAll('[data-stage]');
    stages.forEach(function (stage) {
      stage.classList.remove('is-active', 'is-done');
      var status = stage.querySelector('[data-stage-status]');
      if (status) status.textContent = 'Waiting';
    });
    var resultPanel = document.querySelector('[data-result-panel]');
    if (resultPanel) resultPanel.classList.add('hidden');
    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    if (analyzeBtn) {
      analyzeBtn.classList.remove('is-loading');
      var label = analyzeBtn.querySelector('[data-analyze-label]');
      if (label) label.textContent = 'Analyze recording';
    }
  }

  function runStageSimulation() {
    var stages = Array.prototype.slice.call(document.querySelectorAll('[data-stage]'));
    if (!stages.length) return;

    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    var resultPanel = document.querySelector('[data-result-panel]');
    var label = analyzeBtn ? analyzeBtn.querySelector('[data-analyze-label]') : null;

    resetStages();

    if (analyzeBtn) {
      analyzeBtn.classList.add('is-loading');
      analyzeBtn.disabled = true;
    }
    if (label) label.textContent = 'Analyzing\u2026';

    var perStageMs = 900;

    stages.forEach(function (stage, i) {
      var startDelay = i * perStageMs;
      var doneDelay = startDelay + perStageMs;

      stageTimers.push(setTimeout(function () {
        stages.forEach(function (s) { s.classList.remove('is-active'); });
        stage.classList.add('is-active');
        var status = stage.querySelector('[data-stage-status]');
        if (status) status.textContent = 'Analyzing\u2026';
      }, startDelay));

      stageTimers.push(setTimeout(function () {
        stage.classList.remove('is-active');
        stage.classList.add('is-done');
        var status = stage.querySelector('[data-stage-status]');
        if (status) status.textContent = 'Complete';
      }, doneDelay));
    });

    var totalMs = stages.length * perStageMs;
    stageTimers.push(setTimeout(function () {
      if (analyzeBtn) {
        analyzeBtn.classList.remove('is-loading');
        analyzeBtn.disabled = false;
      }
      if (label) label.textContent = 'Re-analyze recording';
      if (resultPanel) resultPanel.classList.remove('hidden');
    }, totalMs + 200));
  }

  function initAnalyzeButton() {
    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    if (!analyzeBtn) return;
    analyzeBtn.addEventListener('click', function () {
      if (analyzeBtn.disabled) return;
      runStageSimulation();
    });
  }

  /* ---------- Init ---------- */

  document.addEventListener('DOMContentLoaded', function () {
    initLoginPage();
    initNavbar();
    initNavPills();
    initUploadZone();
    initAnalyzeButton();
  });
})();
