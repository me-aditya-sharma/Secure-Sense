/* =========================================================
   SecureSense — shared JS
   Day 2: Audio + Transcript -> POST /analyze -> 4 Signals ->
   Composite Risk -> Decision UI rendering.
   ========================================================= */

(function () {
  'use strict';

  /* ---------- Configuration ---------- */
  var API_BASE = 'http://localhost:8000';
  var MOCK_MODE = true; // Set to false when live backend on API_BASE is confirmed

  if (MOCK_MODE) {
    console.warn(
      '[SecureSense] MOCK_MODE is ENABLED. /analyze requests return realistic multi-signal risk data locally.\n' +
      'Set MOCK_MODE = false in js/main.js to send live network requests to ' + API_BASE + '/analyze'
    );
  }

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

  /* ---------- Nav pill tabs ---------- */

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

  /* ---------- Call Check UI & Analysis Pipeline ---------- */

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  var selectedFile = null;
  var stageTimers = [];
  var isAnalyzing = false;

  function updateAnalyzeButtonState() {
    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    var transcriptInput = document.querySelector('[data-transcript-input]');
    if (!analyzeBtn) return;

    var hasFile = !!selectedFile;
    var hasTranscript = transcriptInput && transcriptInput.value.trim().length > 0;

    if (isAnalyzing) {
      analyzeBtn.disabled = true;
    } else {
      analyzeBtn.disabled = !(hasFile && hasTranscript);
    }
  }

  function hideError() {
    var errorBanner = document.querySelector('[data-error-banner]');
    if (errorBanner) {
      errorBanner.classList.add('hidden');
    }
  }

  function showError(message) {
    var errorBanner = document.querySelector('[data-error-banner]');
    var errorMsgEl = document.querySelector('[data-error-message]');
    if (errorMsgEl) {
      errorMsgEl.textContent = message || 'An unexpected error occurred while analyzing the recording. Please retry.';
    }
    if (errorBanner) {
      errorBanner.classList.remove('hidden');
    }
  }

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

    hideError();

    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    var spinner = document.querySelector('[data-analyze-spinner]');
    var label = document.querySelector('[data-analyze-label]');
    if (analyzeBtn) {
      analyzeBtn.classList.remove('is-loading');
    }
    if (spinner) {
      spinner.classList.add('hidden');
    }
    if (label) {
      label.textContent = 'Analyze recording';
    }
    isAnalyzing = false;
    updateAnalyzeButtonState();
  }

  function startStageAnimation() {
    stageTimers.forEach(function (t) { clearTimeout(t); });
    stageTimers = [];

    var stages = Array.prototype.slice.call(document.querySelectorAll('[data-stage]'));
    if (!stages.length) return;

    stages.forEach(function (stage) {
      stage.classList.remove('is-active', 'is-done');
      var status = stage.querySelector('[data-stage-status]');
      if (status) status.textContent = 'Waiting';
    });

    var perStageMs = 600;

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
  }

  function completeAllStages() {
    stageTimers.forEach(function (t) { clearTimeout(t); });
    stageTimers = [];

    var stages = document.querySelectorAll('[data-stage]');
    stages.forEach(function (stage) {
      stage.classList.remove('is-active');
      stage.classList.add('is-done');
      var status = stage.querySelector('[data-stage-status]');
      if (status) status.textContent = 'Complete';
    });
  }

  /* ---------- SVG Icons & UI helpers ---------- */

  function getBadgeSvg(tier) {
    if (tier === 'low') {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 12 2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg>';
  }

  function getRiskTier(score) {
    var num = Number(score) || 0;
    if (num < 35) return 'low';
    if (num <= 85) return 'medium';
    return 'high';
  }

  function getDecisionInfo(decision, riskTier) {
    var normDecision = (decision || '').toUpperCase().replace('-', '_');
    if (normDecision === 'PROCEED' || (!normDecision && riskTier === 'low')) {
      return {
        action: 'Proceed — call verified safe',
        desc: 'All authentication and conversation checks passed. Caller voiceprint and behaviour match baseline.'
      };
    }
    if (normDecision === 'STEP_UP' || (!normDecision && riskTier === 'medium')) {
      return {
        action: 'Step-up verification required',
        desc: 'Elevated risk signals detected. Prompt caller with an in-band challenge or request secondary confirmation.'
      };
    }
    return {
      action: 'Pause call — verify separately',
      desc: 'End the call and confirm the caller\'s identity through a separate, trusted channel before taking any action.'
    };
  }

  /* ---------- Mock Data Generator ---------- */

  function getMockResponse() {
    return {
      call_event_id: 'evt_sih_' + Math.floor(100000 + Math.random() * 900000),
      signals: {
        voice_authentication: {
          score: 72,
          confidence: 0.94,
          evidence: [
            'Acoustic spectral distance shift from baseline',
            'Pitch contour instability across key phrases',
            'Zero-crossing rate anomaly (synthesis indicator)'
          ],
          status: 'ok'
        },
        behaviour: {
          score: 58,
          confidence: 0.86,
          evidence: [
            'Elevated response latency on security queries',
            'Frequent unnatural hesitation pauses',
            'Scripted cadence inconsistent with history'
          ],
          status: 'ok'
        },
        conversation: {
          score: 92,
          confidence: 0.94,
          evidence: [
            'Urgent fund transfer / account freeze threat',
            'Solicitation of OTP and authorization token',
            'Aggressive authority-impersonation cues'
          ],
          status: 'ok'
        },
        call_trust: {
          score: 88,
          confidence: 0.91,
          evidence: [
            'Unverified VoIP carrier gateway routing',
            'Risk escalated by critical conversation indicators'
          ],
          status: 'ok'
        }
      },
      composite: {
        score: 89,
        risk_level: 'HIGH',
        decision: 'PAUSE'
      },
      challenge_required: true,
      guardian_required: false
    };
  }

  /* ---------- Render response into DOM ---------- */

  function renderAnalysisResult(raw) {
    if (!raw) return;

    var composite = raw.composite || {};
    var compScore = typeof composite.score === 'number' ? composite.score : (typeof raw.composite_risk === 'number' ? raw.composite_risk : 89);
    var compRiskLevel = (composite.risk_level || raw.risk_level || (compScore > 85 ? 'HIGH' : (compScore >= 35 ? 'MEDIUM' : 'LOW'))).toUpperCase();
    var compDecision = composite.decision || raw.decision || (compRiskLevel === 'HIGH' ? 'PAUSE' : (compRiskLevel === 'MEDIUM' ? 'STEP_UP' : 'PROCEED'));

    var compTier = compRiskLevel === 'LOW' ? 'low' : (compRiskLevel === 'MEDIUM' ? 'medium' : 'high');
    var compRiskLabel = compTier.charAt(0).toUpperCase() + compTier.slice(1) + ' risk';
    var decisionDetails = getDecisionInfo(compDecision, compTier);

    // Decision panel
    var panelEl = document.querySelector('[data-decision-panel]');
    var scoreEl = document.querySelector('[data-decision-score]');
    var actionEl = document.querySelector('[data-decision-action]');
    var descEl = document.querySelector('[data-decision-desc]');
    var badgeEl = document.querySelector('[data-decision-badge]');

    if (panelEl) {
      panelEl.classList.remove('decision-panel--low', 'decision-panel--medium', 'decision-panel--high');
      panelEl.classList.add('decision-panel--' + compTier);
    }
    if (scoreEl) {
      scoreEl.textContent = compScore;
    }
    if (actionEl) {
      actionEl.textContent = decisionDetails.action;
    }
    if (descEl) {
      descEl.textContent = decisionDetails.desc;
    }
    if (badgeEl) {
      badgeEl.className = 'risk-badge risk-badge--' + compTier;
      badgeEl.innerHTML = getBadgeSvg(compTier) + ' ' + compRiskLabel;
    }

    // Signals
    var signals = raw.signals || {
      voice_authentication: raw.voice_auth,
      behaviour: raw.behaviour,
      conversation: raw.conversation,
      call_trust: raw.call_trust
    };

    var signalKeys = ['voice_authentication', 'behaviour', 'conversation', 'call_trust'];

    signalKeys.forEach(function (key) {
      var sigData = (signals && signals[key]) || (key === 'voice_authentication' && signals && signals.voice_auth) || {
        score: 50,
        confidence: 0.8,
        evidence: []
      };

      var cardEl = document.querySelector('[data-signal-card="' + key + '"]');
      if (!cardEl) return;

      var sigScore = typeof sigData.score === 'number' ? sigData.score : 50;
      var sigConfidence = typeof sigData.confidence === 'number' ? sigData.confidence : 0.85;
      var sigTier = getRiskTier(sigScore);
      var sigRiskLabel = sigTier.charAt(0).toUpperCase() + sigTier.slice(1) + ' risk';

      var cardBadge = cardEl.querySelector('[data-signal-badge]');
      var cardScore = cardEl.querySelector('[data-signal-score]');
      var cardConfidence = cardEl.querySelector('[data-signal-confidence]');
      var cardBar = cardEl.querySelector('[data-signal-bar]');
      var cardEvidence = cardEl.querySelector('[data-signal-evidence]');

      if (cardBadge) {
        cardBadge.className = 'risk-badge risk-badge--' + sigTier;
        cardBadge.innerHTML = getBadgeSvg(sigTier) + ' ' + sigRiskLabel;
      }
      if (cardScore) {
        cardScore.innerHTML = sigScore + ' <span>/ 100</span>';
      }
      if (cardConfidence) {
        var confPercent = Math.round(sigConfidence <= 1 ? sigConfidence * 100 : sigConfidence);
        cardConfidence.textContent = confPercent + '% confidence';
      }
      if (cardBar) {
        cardBar.className = 'signal-card__bar-fill signal-card__bar-fill--' + sigTier;
        cardBar.style.width = Math.max(0, Math.min(100, sigScore)) + '%';
      }
      if (cardEvidence) {
        cardEvidence.innerHTML = '';
        var evidenceList = Array.isArray(sigData.evidence) ? sigData.evidence : [];
        if (!evidenceList.length) {
          evidenceList = ['Analyzed against security baseline'];
        }
        evidenceList.forEach(function (item) {
          var tag = document.createElement('span');
          tag.className = 'evidence-tag';
          tag.textContent = item;
          cardEvidence.appendChild(tag);
        });
      }
    });

    var resultPanel = document.querySelector('[data-result-panel]');
    if (resultPanel) {
      resultPanel.classList.remove('hidden');
    }
  }

  /* ---------- Execute Analysis (Mock or Real Fetch) ---------- */

  function executeAnalysis() {
    if (isAnalyzing) return;
    var transcriptInput = document.querySelector('[data-transcript-input]');
    var transcriptText = transcriptInput ? transcriptInput.value.trim() : '';

    if (!selectedFile || !transcriptText) {
      showError('Please provide both an audio recording and the call transcript before analyzing.');
      return;
    }

    isAnalyzing = true;
    hideError();

    var analyzeBtn = document.querySelector('[data-analyze-btn]');
    var spinner = document.querySelector('[data-analyze-spinner]');
    var label = document.querySelector('[data-analyze-label]');

    if (analyzeBtn) {
      analyzeBtn.classList.add('is-loading');
      analyzeBtn.disabled = true;
    }
    if (spinner) {
      spinner.classList.remove('hidden');
    }
    if (label) {
      label.textContent = 'Analyzing\u2026';
    }

    startStageAnimation();

    function onAnalysisComplete(data) {
      completeAllStages();
      renderAnalysisResult(data);

      isAnalyzing = false;
      if (analyzeBtn) {
        analyzeBtn.classList.remove('is-loading');
        analyzeBtn.disabled = false;
      }
      if (spinner) {
        spinner.classList.add('hidden');
      }
      if (label) {
        label.textContent = 'Re-analyze recording';
      }
    }

    function onAnalysisError(err) {
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

      showError(err && err.message ? err.message : 'Network error or backend unavailable. Please ensure the server is running and retry.');

      isAnalyzing = false;
      if (analyzeBtn) {
        analyzeBtn.classList.remove('is-loading');
        analyzeBtn.disabled = false;
      }
      if (spinner) {
        spinner.classList.add('hidden');
      }
      if (label) {
        label.textContent = 'Analyze recording';
      }
      updateAnalyzeButtonState();
    }

    if (MOCK_MODE) {
      // Simulate backend roundtrip time with stage stepping
      setTimeout(function () {
        try {
          var mockData = getMockResponse();
          onAnalysisComplete(mockData);
        } catch (e) {
          onAnalysisError(e);
        }
      }, 2500);
      return;
    }

    // Real API fetch
    var user = getUser();
    var formData = new FormData();
    formData.append('audio', selectedFile);
    formData.append('transcript', transcriptText);
    formData.append('metadata', JSON.stringify({
      user_id: user && (user.name || user.phone) ? (user.name + ' (' + (user.phone || '') + ')') : 'demo_user',
      timestamp: new Date().toISOString()
    }));

    fetch(API_BASE + '/analyze', {
      method: 'POST',
      body: formData
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error('Backend returned HTTP ' + res.status + ' (' + res.statusText + ')');
        }
        return res.json();
      })
      .then(function (data) {
        onAnalysisComplete(data);
      })
      .catch(function (err) {
        onAnalysisError(err);
      });
  }

  /* ---------- File Upload & Form Event Wiring ---------- */

  function initUploadZone() {
    var zone = document.querySelector('[data-upload-zone]');
    var input = document.querySelector('[data-upload-input]');
    var chip = document.querySelector('[data-file-chip]');
    var chipName = document.querySelector('[data-file-name]');
    var chipMeta = document.querySelector('[data-file-meta]');
    var removeBtn = document.querySelector('[data-file-remove]');
    var transcriptInput = document.querySelector('[data-transcript-input]');
    var analyzeBtn = document.querySelector('[data-analyze-btn]');

    if (!zone || !input) return;

    function showFile(file) {
      if (!file) return;
      selectedFile = file;
      if (chipName) chipName.textContent = file.name;
      if (chipMeta) chipMeta.textContent = formatFileSize(file.size);
      if (chip) chip.classList.remove('hidden');
      hideError();
      updateAnalyzeButtonState();
    }

    function clearFile() {
      selectedFile = null;
      input.value = '';
      if (chip) chip.classList.add('hidden');
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
      if (input.files && input.files[0]) {
        showFile(input.files[0]);
      }
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

    if (transcriptInput) {
      transcriptInput.addEventListener('input', function () {
        hideError();
        updateAnalyzeButtonState();
      });
    }

    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', function () {
        if (analyzeBtn.disabled || isAnalyzing) return;
        executeAnalysis();
      });
    }
  }

  /* ---------- Init ---------- */

  document.addEventListener('DOMContentLoaded', function () {
    initLoginPage();
    initNavbar();
    initNavPills();
    initUploadZone();
  });
})();
