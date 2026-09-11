
/* =========================================================
   SecureSense — shared JS
   Day 2: Audio + Transcript -> POST /analyze -> 4 Signals ->
          Composite Risk -> Decision UI rendering.
   Day 3: Identity Challenge Flow (Medium Risk) +
          Guardian Alert & Escalation Flow (High Risk) +
          Audit Trail Section.
   ========================================================= */

(function () {
  'use strict';

  /* ---------- Configuration ---------- */
  var API_BASE = 'http://localhost:8000';
  // http://localhost:8000
  // https://poet-laurel-sandworm.ngrok-free.dev
  var MOCK_MODE = false; // Set to false when live backend on API_BASE is confirmed

  if (MOCK_MODE) {
    console.warn(
      '[SecureSense] MOCK_MODE is ENABLED. /analyze requests return realistic multi-signal risk data locally.\n' +
      'Set MOCK_MODE = false in js/main.js to send live network requests to ' + API_BASE + '/analyze'
    );
  }

  var SESSION_KEY = 'securesense_user';
  var currentCallEventId = 'evt_' + Date.now();

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

  function getSessionSeed(extra) {
    var user = getUser();
    var seedStr = (user ? (user.name || '') + (user.phone || '') : 'demo_seed') + '_' + (currentCallEventId || '') + '_' + (extra || '');
    var hash = 0;
    for (var i = 0; i < seedStr.length; i++) {
      hash = ((hash << 5) - hash) + seedStr.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
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
  var lastChallengeScore = 0;

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
    hideChallengePanel();
    hideGuardianPanel();

    lastChallengeScore = 0;
    var auditPanel = document.querySelector('[data-audit-panel]');
    if (auditPanel) auditPanel.classList.add('hidden');

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

  /* ---------- Challenge & Guardian Panels Handling ---------- */

  var selectedChallengeFile = null;
  var isChallengeVerifying = false;
  var guardianTimer = null;

  function resetChallengePanel() {
    selectedChallengeFile = null;
    isChallengeVerifying = false;

    var input = document.querySelector('[data-challenge-upload-input]');
    if (input) input.value = '';

    var chip = document.querySelector('[data-challenge-file-chip]');
    if (chip) chip.classList.add('hidden');

    var resultBox = document.querySelector('[data-challenge-result]');
    if (resultBox) resultBox.classList.add('hidden');

    var btn = document.querySelector('[data-challenge-verify-btn]');
    var spinner = document.querySelector('[data-challenge-spinner]');
    var label = document.querySelector('[data-challenge-label]');
    if (btn) {
      btn.disabled = true;
      btn.classList.remove('is-loading');
    }
    if (spinner) spinner.classList.add('hidden');
    if (label) label.textContent = 'Verify caller identity';
  }

  function showChallengePanel() {
    resetChallengePanel();
    var panel = document.querySelector('[data-challenge-panel]');
    if (panel) panel.classList.remove('hidden');
  }

  function hideChallengePanel() {
    var panel = document.querySelector('[data-challenge-panel]');
    if (panel) panel.classList.add('hidden');
  }

  function resetGuardianPanel() {
    if (guardianTimer) {
      clearTimeout(guardianTimer);
      guardianTimer = null;
    }

    var statusBox = document.querySelector('[data-guardian-status-box]');
    if (statusBox) statusBox.classList.remove('hidden');

    var statusText = document.querySelector('[data-guardian-status-text]');
    if (statusText) statusText.textContent = 'Alert sent — awaiting response';

    var spinner = document.querySelector('[data-guardian-spinner]');
    if (spinner) spinner.classList.remove('hidden');

    var banner = document.querySelector('[data-guardian-banner]');
    if (banner) banner.classList.add('hidden');
  }

  function showGuardianPanel() {
    resetGuardianPanel();
    var panel = document.querySelector('[data-guardian-panel]');
    if (panel) panel.classList.remove('hidden');
  }

  function hideGuardianPanel() {
    if (guardianTimer) {
      clearTimeout(guardianTimer);
      guardianTimer = null;
    }
    var panel = document.querySelector('[data-guardian-panel]');
    if (panel) panel.classList.add('hidden');
  }

  function applyGuardianOutcome(isApproved) {
    if (guardianTimer) {
      clearTimeout(guardianTimer);
      guardianTimer = null;
    }

    var statusBox = document.querySelector('[data-guardian-status-box]');
    if (statusBox) statusBox.classList.add('hidden');

    var banner = document.querySelector('[data-guardian-banner]');
    var icon = document.querySelector('[data-guardian-banner-icon]');
    var title = document.querySelector('[data-guardian-banner-title]');
    var desc = document.querySelector('[data-guardian-banner-desc]');

    if (!banner) return;

    if (isApproved) {
      banner.className = 'guardian-banner guardian-banner--approved mt-3';
      if (icon) {
        icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 12 2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg>';
      }
      if (title) title.textContent = 'Guardian approved — call may proceed with caution';
      if (desc) desc.textContent = 'Rohan Sharma confirmed caller authorization via biometric mobile push approval.';
    } else {
      banner.className = 'guardian-banner guardian-banner--denied mt-3';
      if (icon) {
        icon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
      }
      if (title) title.textContent = 'Guardian denied — call blocked, transaction paused';
      if (desc) desc.textContent = 'Guardian rejected verification request. High-risk alert recorded and call flagged for fraud review.';
    }

    banner.classList.remove('hidden');
  }

  function startGuardianAutoSimulation() {
    if (guardianTimer) clearTimeout(guardianTimer);

    // Deterministic outcome per session (approx 70% approve / 30% deny)
    var isApproved = (getSessionSeed('guardian_auto') % 10) < 7;

    guardianTimer = setTimeout(function () {
      applyGuardianOutcome(isApproved);
    }, 2000);
  }

  function initGuardianControls() {
    var approveBtn = document.querySelector('[data-guardian-approve-btn]');
    var denyBtn = document.querySelector('[data-guardian-deny-btn]');

    if (approveBtn) {
      approveBtn.addEventListener('click', function () {
        applyGuardianOutcome(true);
      });
    }

    if (denyBtn) {
      denyBtn.addEventListener('click', function () {
        applyGuardianOutcome(false);
      });
    }
  }

  function renderChallengeResult(res) {
    isChallengeVerifying = false;

    var btn = document.querySelector('[data-challenge-verify-btn]');
    var spinner = document.querySelector('[data-challenge-spinner]');
    var label = document.querySelector('[data-challenge-label]');

    if (spinner) spinner.classList.add('hidden');
    if (btn) {
      btn.classList.remove('is-loading');
      btn.disabled = false;
    }
    if (label) label.textContent = 'Re-verify identity';

    var resultBox = document.querySelector('[data-challenge-result]');
    var badge = document.querySelector('[data-challenge-badge]');
    var title = document.querySelector('[data-challenge-title]');
    var desc = document.querySelector('[data-challenge-desc]');
    var evidence = document.querySelector('[data-challenge-evidence]');

    if (!resultBox) return;

    var isMatch = res && res.status === 'match';
    lastChallengeScore = (res && typeof res.score === 'number') ? res.score : (isMatch ? 88 : 24);

    // Update challenge score tile in Audit Trail if visible
    var chalTile = document.querySelector('[data-audit-score-challenge]');
    if (chalTile) chalTile.textContent = lastChallengeScore;

    if (isMatch) {
      if (badge) {
        badge.className = 'risk-badge risk-badge--low';
        badge.innerHTML = getBadgeSvg('low') + ' Match confirmed';
      }
      if (title) title.textContent = 'Identity confirmed';
      if (desc) desc.textContent = 'Second voice sample matched the enrolled voiceprint baseline. Authenticity verified.';
    } else {
      if (badge) {
        badge.className = 'risk-badge risk-badge--high';
        badge.innerHTML = getBadgeSvg('high') + ' Mismatch detected';
      }
      if (title) title.textContent = 'Identity could not be confirmed — escalate to Guardian';
      if (desc) desc.textContent = 'Second voice sample failed acoustic match against enrolled baseline. Escalating call to Guardian Protocol.';
    }

    if (evidence) {
      evidence.innerHTML = '';
      var items = (res && Array.isArray(res.evidence)) ? res.evidence : (isMatch ? ['Voiceprint matches enrolled sample', 'Consistent pitch and cadence'] : ['Voiceprint mismatch detected', 'Acoustic feature deviation exceeds threshold']);
      items.forEach(function (item) {
        var tag = document.createElement('span');
        tag.className = 'evidence-tag';
        tag.textContent = item;
        evidence.appendChild(tag);
      });
    }

    resultBox.classList.remove('hidden');

    if (!isMatch) {
      // Escalate to Guardian
      showGuardianPanel();
      startGuardianAutoSimulation();
    }
  }

  function executeChallenge() {
    if (isChallengeVerifying || !selectedChallengeFile) return;

    isChallengeVerifying = true;
    var btn = document.querySelector('[data-challenge-verify-btn]');
    var spinner = document.querySelector('[data-challenge-spinner]');
    var label = document.querySelector('[data-challenge-label]');

    if (btn) {
      btn.classList.add('is-loading');
      btn.disabled = true;
    }
    if (spinner) spinner.classList.remove('hidden');
    if (label) label.textContent = 'Verifying\u2026';

    if (MOCK_MODE) {
      setTimeout(function () {
        // Deterministic mock outcome per session (~70% match / 30% no_match)
        var isMatch = (getSessionSeed('challenge_result') % 10) < 7;
        var mockResult = isMatch
          ? {
            status: 'match',
            score: 88,
            confidence: 0.93,
            evidence: [
              'Voiceprint matches enrolled sample',
              'Consistent pitch and cadence baseline',
              'Acoustic spectral match confirmed (88/100)'
            ]
          }
          : {
            status: 'no_match',
            score: 24,
            confidence: 0.91,
            evidence: [
              'Voiceprint mismatch detected',
              'Acoustic feature deviation exceeds threshold',
              'Spectral similarity score: 24/100'
            ]
          };
        renderChallengeResult(mockResult);
      }, 1500);
      return;
    }

    var formData = new FormData();
    formData.append('call_event_id', currentCallEventId);
    formData.append('second_clip', selectedChallengeFile);

    fetch(API_BASE + '/challenge', {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true'
      },
      body: formData
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Challenge verification failed');
        return res.json();
      })
      .then(function (data) {
        var isMatch = (data.status === 'match' || data.status === 'completed' || (data.challenge_score && data.challenge_score.score >= 50));
        renderChallengeResult({
          status: isMatch ? 'match' : 'no_match',
          score: data.challenge_score ? data.challenge_score.score : (isMatch ? 88 : 24),
          confidence: data.challenge_score ? data.challenge_score.confidence : 0.9,
          evidence: data.challenge_score && data.challenge_score.evidence ? data.challenge_score.evidence : []
        });
      })
      .catch(function () {
        renderChallengeResult({
          status: 'no_match',
          score: 20,
          confidence: 0.85,
          evidence: ['Voice match challenge rejected by backend']
        });
      });
  }

  function initChallengeZone() {
    var zone = document.querySelector('[data-challenge-upload-zone]');
    var input = document.querySelector('[data-challenge-upload-input]');
    var chip = document.querySelector('[data-challenge-file-chip]');
    var chipName = document.querySelector('[data-challenge-file-name]');
    var chipMeta = document.querySelector('[data-challenge-file-meta]');
    var removeBtn = document.querySelector('[data-challenge-file-remove]');
    var verifyBtn = document.querySelector('[data-challenge-verify-btn]');

    if (!zone || !input) return;

    function showChallengeFile(file) {
      if (!file) return;
      selectedChallengeFile = file;
      if (chipName) chipName.textContent = file.name;
      if (chipMeta) chipMeta.textContent = formatFileSize(file.size);
      if (chip) chip.classList.remove('hidden');
      if (verifyBtn) verifyBtn.disabled = false;
    }

    function clearChallengeFile() {
      selectedChallengeFile = null;
      input.value = '';
      if (chip) chip.classList.add('hidden');
      if (verifyBtn) verifyBtn.disabled = true;
      var resultBox = document.querySelector('[data-challenge-result]');
      if (resultBox) resultBox.classList.add('hidden');
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
        showChallengeFile(input.files[0]);
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
        showChallengeFile(files[0]);
      }
    });

    if (removeBtn) {
      removeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        clearChallengeFile();
      });
    }

    if (verifyBtn) {
      verifyBtn.addEventListener('click', function () {
        if (verifyBtn.disabled || isChallengeVerifying) return;
        executeChallenge();
      });
    }
  }

  /* ---------- Audit Trail Handling ---------- */

  var fullAuditHash = '';

  function formatReadableDate(dateInput) {
    var d = dateInput ? new Date(dateInput) : new Date();
    if (isNaN(d.getTime())) d = new Date();
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var day = d.getDate();
    var month = months[d.getMonth()];
    var year = d.getFullYear();
    var hours = String(d.getHours()).padStart(2, '0');
    var minutes = String(d.getMinutes()).padStart(2, '0');
    return day + ' ' + month + ' ' + year + ', ' + hours + ':' + minutes;
  }

  function truncateMiddle(str, frontChars, backChars) {
    if (!str) return '—';
    var f = frontChars || 8;
    var b = backChars || 9;
    if (str.length <= f + b + 3) return str;
    return str.substring(0, f) + '...' + str.substring(str.length - b);
  }

  function showAuditUnavailable() {
    var auditPanel = document.querySelector('[data-audit-panel]');
    var auditError = document.querySelector('[data-audit-error]');
    var metaRow = document.querySelector('.audit-meta-row');
    var scoresSec = document.querySelector('.audit-scores-section');
    var hashSec = document.querySelector('.audit-hash-section');
    if (metaRow) metaRow.classList.add('hidden');
    if (scoresSec) scoresSec.classList.add('hidden');
    if (hashSec) hashSec.classList.add('hidden');
    if (auditError) auditError.classList.remove('hidden');
    if (auditPanel) auditPanel.classList.remove('hidden');
  }

  function renderAuditRecord(auditData) {
    if (!auditData) return;
    var auditPanel = document.querySelector('[data-audit-panel]');
    var auditError = document.querySelector('[data-audit-error]');
    var metaRow = document.querySelector('.audit-meta-row');
    var scoresSec = document.querySelector('.audit-scores-section');
    var hashSec = document.querySelector('.audit-hash-section');

    if (auditError) auditError.classList.add('hidden');
    if (metaRow) metaRow.classList.remove('hidden');
    if (scoresSec) scoresSec.classList.remove('hidden');
    if (hashSec) hashSec.classList.remove('hidden');

    var timeEl = document.querySelector('[data-audit-timestamp]');
    var decisionBadge = document.querySelector('[data-audit-decision-badge]');
    var voiceEl = document.querySelector('[data-audit-score-voice]');
    var behaviourEl = document.querySelector('[data-audit-score-behaviour]');
    var convEl = document.querySelector('[data-audit-score-conversation]');
    var trustEl = document.querySelector('[data-audit-score-calltrust]');
    var chalEl = document.querySelector('[data-audit-score-challenge]');
    var hashEl = document.querySelector('[data-audit-hash]');

    if (timeEl) timeEl.textContent = formatReadableDate(auditData.timestamp);

    var rawDecision = (auditData.decision || 'PAUSE').toUpperCase().replace('-', '_');
    var decisionLabel = rawDecision === 'PROCEED' ? 'Proceed' : (rawDecision === 'STEP_UP' ? 'Step-up' : 'Pause');
    var decisionTier = rawDecision === 'PROCEED' ? 'low' : (rawDecision === 'STEP_UP' ? 'medium' : 'high');

    if (decisionBadge) {
      decisionBadge.className = 'risk-badge risk-badge--' + decisionTier;
      decisionBadge.innerHTML = getBadgeSvg(decisionTier) + ' ' + decisionLabel;
    }

    var scores = auditData.scores || {};
    if (voiceEl) voiceEl.textContent = (scores.voice_auth !== undefined) ? scores.voice_auth : '—';
    if (behaviourEl) behaviourEl.textContent = (scores.behaviour !== undefined) ? scores.behaviour : '—';
    if (convEl) convEl.textContent = (scores.conversation !== undefined) ? scores.conversation : '—';
    if (trustEl) trustEl.textContent = (scores.call_trust !== undefined) ? scores.call_trust : '—';
    if (chalEl) {
      var cVal = (scores.challenge !== undefined && scores.challenge !== null) ? scores.challenge : lastChallengeScore;
      chalEl.textContent = (cVal > 0) ? cVal : 'N/A';
    }

    fullAuditHash = auditData.audit_hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
    if (hashEl) hashEl.textContent = truncateMiddle(fullAuditHash, 8, 9);

    if (auditPanel) auditPanel.classList.remove('hidden');
  }

  function fetchAuditTrail(callEventId, analysisData) {
    if (MOCK_MODE) {
      var signals = (analysisData && analysisData.signals) || {};
      var voiceScore = (signals.voice_authentication && signals.voice_authentication.score) !== undefined ? signals.voice_authentication.score : 72;
      var behaviourScore = (signals.behaviour && signals.behaviour.score) !== undefined ? signals.behaviour.score : 58;
      var conversationScore = (signals.conversation && signals.conversation.score) !== undefined ? signals.conversation.score : 92;
      var callTrustScore = (signals.call_trust && signals.call_trust.score) !== undefined ? signals.call_trust.score : 88;
      var comp = (analysisData && analysisData.composite) || {};
      var decisionStr = comp.decision || 'PAUSE';

      var mockAudit = {
        timestamp: new Date().toISOString(),
        user_id: (getUser() && getUser().name) || 'demo_user',
        decision: decisionStr,
        scores: {
          voice_auth: voiceScore,
          behaviour: behaviourScore,
          conversation: conversationScore,
          call_trust: callTrustScore,
          challenge: lastChallengeScore || 0
        },
        audit_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
      };
      renderAuditRecord(mockAudit);
      return;
    }

    fetch(API_BASE + '/audit?call_event_id=' + encodeURIComponent(callEventId), {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true'
      }
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Audit record not available');
        return res.json();
      })
      .then(function (auditData) {
        if (auditData && (!auditData.scores || Object.keys(auditData.scores).length === 0)) {
          auditData.scores = {
            voice_auth: analysisData && analysisData.voice_auth ? analysisData.voice_auth.score : '—',
            behaviour: analysisData && analysisData.behaviour ? analysisData.behaviour.score : '—',
            conversation: analysisData && analysisData.conversation ? analysisData.conversation.score : '—',
            call_trust: analysisData && analysisData.call_trust ? analysisData.call_trust.score : '—'
          };
        }
        renderAuditRecord(auditData);
      })
      .catch(function () {
        showAuditUnavailable();
      });
  }

  function fallbackCopy(text, labelEl) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      if (labelEl) labelEl.textContent = 'Copied!';
      setTimeout(function () {
        if (labelEl) labelEl.textContent = 'Copy';
      }, 2000);
    } catch (e) { }
    document.body.removeChild(ta);
  }

  function initAuditCopyBtn() {
    var copyBtn = document.querySelector('[data-audit-copy-btn]');
    var copyLabel = document.querySelector('[data-audit-copy-label]');
    if (!copyBtn) return;

    copyBtn.addEventListener('click', function () {
      if (!fullAuditHash) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(fullAuditHash).then(function () {
          if (copyLabel) copyLabel.textContent = 'Copied!';
          setTimeout(function () {
            if (copyLabel) copyLabel.textContent = 'Copy';
          }, 2000);
        }).catch(function () {
          fallbackCopy(fullAuditHash, copyLabel);
        });
      } else {
        fallbackCopy(fullAuditHash, copyLabel);
      }
    });
  }

  /* ---------- Render response into DOM ---------- */

  function renderAnalysisResult(raw) {
    if (!raw) return;

    currentCallEventId = raw.call_event_id || ('evt_' + Date.now());

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

    // Day 3: Challenge vs Guardian Flow conditional rendering
    if (compTier === 'low') {
      hideChallengePanel();
      hideGuardianPanel();
    } else if (compTier === 'medium') {
      showChallengePanel();
      hideGuardianPanel();
    } else if (compTier === 'high') {
      hideChallengePanel();
      showGuardianPanel();
      startGuardianAutoSimulation();
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

    // Automatically fetch Audit Trail once analysis completes
    fetchAuditTrail(currentCallEventId, raw);
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
      headers: {
        'ngrok-skip-browser-warning': 'true'
      },
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

  function loadDashboardStats() {
    var totalCallsEl = document.getElementById('dash-total-calls');
    var flaggedCallsEl = document.getElementById('dash-flagged-calls');
    var voiceMatchesEl = document.getElementById('dash-voice-matches');
    var historyListEl = document.getElementById('dash-history-list');
    
    if (!totalCallsEl) return; // Not on dashboard page
    
    fetch(API_BASE + '/dashboard_stats', {
      headers: { 'ngrok-skip-browser-warning': 'true' }
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (totalCallsEl) totalCallsEl.textContent = data.total_calls || 0;
      if (flaggedCallsEl) flaggedCallsEl.textContent = data.flagged_calls || 0;
      if (voiceMatchesEl) voiceMatchesEl.textContent = data.voice_matches || 0;
      
      if (historyListEl && data.recent_history) {
        historyListEl.innerHTML = '';
        if (data.recent_history.length === 0) {
          historyListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--color-text-muted);">No recent calls found.</div>';
        } else {
          data.recent_history.forEach(function(call) {
            var riskLevel = (call.risk_level || 'LOW').toLowerCase();
            var metaStr = '{}';
            try { metaStr = JSON.parse(call.metadata); } catch(e) {}
            var phone = metaStr.user_id || 'Unknown';
            var title = 'Call Analysis';
            
            var evidence = '';
            if (call.voice_evidence && call.voice_evidence.length > 0) evidence += call.voice_evidence[0] + ', ';
            if (call.conversation_evidence && call.conversation_evidence.length > 0) evidence += call.conversation_evidence[0];
            if (!evidence) evidence = 'Analyzed against security baseline';
            if (evidence.endsWith(', ')) evidence = evidence.slice(0, -2);
            
            var timeAgo = 'Just now'; // Simplified
            
            var html = '<div class="status-dot-item">' +
              '<span class="status-dot status-dot--' + riskLevel + '"></span>' +
              '<div class="status-dot-item__body">' +
                '<div class="status-dot-item__title">' + title + '</div>' +
                '<div class="status-dot-item__phone">' + phone + '</div>' +
                '<div class="status-dot-item__meta">' + evidence + '</div>' +
              '</div>' +
              '<span class="status-dot-item__time">' + timeAgo + '</span>' +
            '</div>';
            historyListEl.insertAdjacentHTML('beforeend', html);
          });
        }
      }
    })
    .catch(function(err) {
      console.error('Failed to load dashboard stats:', err);
    });
  }

  /* ---------- Init ---------- */

  document.addEventListener('DOMContentLoaded', function () {
    initLoginPage();
    initNavbar();
    initNavPills();
    initUploadZone();
    initChallengeZone();
    initGuardianControls();
    initAuditCopyBtn();
    loadDashboardStats();
  });
})();

