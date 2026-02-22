/**
 * ResumeAI · Frontend Application Logic
 * State machine: UPLOAD → PROCESSING → RESULT
 */

'use strict';

// ─── Constants ───────────────────────────────────────────────────────────────
const API_BASE = '';        // Same-origin serving from FastAPI
const MAX_FILE_MB = 10;

// Processing step messages
const STEP_MESSAGES = [
  'Parsing job description…',
  'Extracting resume sections…',
  'Running surgical AI rewrite (Groq)…',
  'Injecting text into original format…',
  'Calculating ATS match score…',
];

// ─── State ───────────────────────────────────────────────────────────────────
let state = {
  file: null,
  sessionId: null,
  activeTab: 'url',     // 'url' | 'paste'
};

// ─── DOM Refs ────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const D = {
  dropzone:       $('dropzone'),
  fileInput:      $('fileInput'),
  filePreview:    $('filePreview'),
  fileName:       $('fileName'),
  fileSize:       $('fileSize'),
  fileTypeIcon:   $('fileTypeIcon'),
  fileRemove:     $('fileRemove'),
  tabUrl:         $('tab-url'),
  tabPaste:       $('tab-paste'),
  jdUrlPanel:     $('jd-url-panel'),
  jdPastePanel:   $('jd-paste-panel'),
  jdUrl:          $('jdUrl'),
  jdText:         $('jdText'),
  btnOptimize:    $('btnOptimize'),
  submitHint:     $('submitHint'),

  sectionUpload:     $('section-upload'),
  sectionProcessing: $('section-processing'),
  sectionResult:     $('section-result'),
  processingStep:    $('processingStep'),

  resultJobTitle: $('resultJobTitle'),
  gaugeScore:     $('gaugeScore'),
  scoreArc:       $('scoreArc'),
  scoreKeyword:   $('scoreKeyword'),
  scoreRelevancy: $('scoreRelevancy'),
  scoreFormat:    $('scoreFormat'),
  barKeyword:     $('barKeyword'),
  barRelevancy:   $('barRelevancy'),
  barFormat:      $('barFormat'),
  resultFeedback: $('resultFeedback'),
  matchedKeywords:$('matchedKeywords'),
  missingKeywords:$('missingKeywords'),
  sectionsFound:  $('sectionsFound'),
  btnDownload:    $('btnDownload'),
  btnReset:       $('btnReset'),

  errorToast:     $('errorToast'),
  errorMessage:   $('errorMessage'),
  errorClose:     $('errorClose'),
};

// ─── File Handling ────────────────────────────────────────────────────────────
D.dropzone.addEventListener('click', () => D.fileInput.click());
D.dropzone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') D.fileInput.click();
});
D.fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) setFile(e.target.files[0]);
});
D.dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  D.dropzone.classList.add('dragover');
});
D.dropzone.addEventListener('dragleave', () => D.dropzone.classList.remove('dragover'));
D.dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  D.dropzone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});
D.fileRemove.addEventListener('click', clearFile);

function setFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    showError('Please upload a PDF or DOCX file.');
    return;
  }
  if (file.size > MAX_FILE_MB * 1024 * 1024) {
    showError(`File is too large. Maximum size is ${MAX_FILE_MB}MB.`);
    return;
  }
  state.file = file;
  D.fileName.textContent = file.name;
  D.fileSize.textContent = formatBytes(file.size);
  D.fileTypeIcon.textContent = ext === 'pdf' ? '📄' : '📝';
  D.filePreview.classList.remove('hidden');
  D.dropzone.classList.add('hidden');
  updateSubmitState();
}

function clearFile() {
  state.file = null;
  D.fileInput.value = '';
  D.filePreview.classList.add('hidden');
  D.dropzone.classList.remove('hidden');
  updateSubmitState();
}

// ─── JD Tabs ─────────────────────────────────────────────────────────────────
[D.tabUrl, D.tabPaste].forEach((tab) => {
  tab.addEventListener('click', () => {
    const which = tab.dataset.tab;
    state.activeTab = which;
    D.tabUrl.classList.toggle('active', which === 'url');
    D.tabPaste.classList.toggle('active', which === 'paste');
    D.jdUrlPanel.classList.toggle('hidden', which !== 'url');
    D.jdPastePanel.classList.toggle('hidden', which !== 'paste');
    updateSubmitState();
  });
});

D.jdUrl.addEventListener('input', updateSubmitState);
D.jdText.addEventListener('input', updateSubmitState);

// ─── Submit State ─────────────────────────────────────────────────────────────
function updateSubmitState() {
  const hasFile = !!state.file;
  const hasJd =
    (state.activeTab === 'url' && D.jdUrl.value.trim().length > 5) ||
    (state.activeTab === 'paste' && D.jdText.value.trim().length > 30);

  D.btnOptimize.disabled = !(hasFile && hasJd);
  D.submitHint.textContent = !hasFile
    ? 'Upload a resume to get started'
    : !hasJd
    ? 'Add a job description URL or paste the text'
    : 'Ready to optimize! Click the button above.';
}

// ─── Optimization Pipeline ────────────────────────────────────────────────────
D.btnOptimize.addEventListener('click', startOptimize);

async function startOptimize() {
  if (!state.file) return;

  showSection('processing');
  animateSteps();

  const formData = new FormData();
  formData.append('file', state.file);

  if (state.activeTab === 'url' && D.jdUrl.value.trim()) {
    formData.append('jd_url', D.jdUrl.value.trim());
  }
  if (D.jdText.value.trim()) {
    formData.append('jd_text', D.jdText.value.trim());
  }

  try {
    const res = await fetch(`${API_BASE}/api/optimize`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'Unknown server error' }));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    state.sessionId = data.session_id;
    // Wait for animations to finish (min 800ms visual polish)
    await sleep(600);
    showResults(data);
  } catch (err) {
    showSection('upload');
    showError(err.message || 'Optimization failed. Please try again.');
  }
}

// ─── Step Animation ───────────────────────────────────────────────────────────
let stepTimer = null;

function animateSteps() {
  clearAllSteps();
  let step = 0;

  function advance() {
    if (step > 0) markStepDone(step);
    step++;
    if (step > 5) return;
    markStepActive(step);
    D.processingStep.textContent = STEP_MESSAGES[step - 1];
    stepTimer = setTimeout(advance, 2200);
  }
  advance();
}

function clearAllSteps() {
  if (stepTimer) clearTimeout(stepTimer);
  for (let i = 1; i <= 5; i++) {
    const el = $(`step-${i}`);
    if (el) el.className = 'step-item';
  }
}
function markStepActive(n) {
  const el = $(`step-${n}`);
  if (el) el.classList.add('active');
}
function markStepDone(n) {
  const el = $(`step-${n}`);
  if (el) { el.classList.remove('active'); el.classList.add('done'); }
}

// ─── Results Display ──────────────────────────────────────────────────────────
function showResults(data) {
  const score = data.ats_score || {};
  const kw = data.keyword_overlap || {};
  const sections = data.sections_found || {};

  // Mark all steps done
  for (let i = 1; i <= 5; i++) markStepDone(i);

  showSection('result');

  D.resultJobTitle.textContent = data.job_title || 'Optimized Resume';
  D.resultFeedback.textContent = score.feedback || 'Resume optimized successfully.';

  const total = score.total || 0;
  const kwScore = score.keyword_match || 0;
  const relScore = score.role_relevancy || 0;
  const fmtScore = score.formatting_simplicity || 0;

  // Animate score counter
  animateCounter(D.gaugeScore, 0, total, 1500);

  // Animate gauge arc (circumference = 2π×80 ≈ 502.65)
  const circ = 2 * Math.PI * 80;
  setTimeout(() => {
    const fill = (total / 100) * circ;
    D.scoreArc.setAttribute('stroke-dasharray', `${fill.toFixed(1)} ${(circ - fill).toFixed(1)}`);
  }, 100);

  // Score bars
  setTimeout(() => {
    D.scoreKeyword.textContent = `${kwScore}/40`;
    D.scoreRelevancy.textContent = `${relScore}/40`;
    D.scoreFormat.textContent = `${fmtScore}/20`;
    D.barKeyword.style.width = `${(kwScore / 40) * 100}%`;
    D.barRelevancy.style.width = `${(relScore / 40) * 100}%`;
    D.barFormat.style.width = `${(fmtScore / 20) * 100}%`;
  }, 200);

  // Keywords
  const matched = score.top_matched_keywords || kw.matched?.slice(0, 8) || [];
  const missing = score.missing_keywords || kw.missing?.slice(0, 8) || [];
  renderKeywordTags(D.matchedKeywords, matched, 'keyword-tag');
  renderKeywordTags(D.missingKeywords, missing, 'keyword-tag');

  // Sections found
  const total_blocks = (sections.summary_blocks || 0) + (sections.experience_blocks || 0);
  D.sectionsFound.textContent = `${total_blocks} text block${total_blocks !== 1 ? 's' : ''} rewritten`;

  // Download link
  D.btnDownload.href = `${API_BASE}/api/download/${state.sessionId}`;
}

function renderKeywordTags(container, keywords, className) {
  container.innerHTML = '';
  if (!keywords.length) {
    container.innerHTML = '<span style="font-size:0.72rem;color:var(--text-muted)">—</span>';
    return;
  }
  keywords.forEach((kw) => {
    const tag = document.createElement('span');
    tag.className = className;
    tag.textContent = kw;
    container.appendChild(tag);
  });
}

function animateCounter(el, from, to, duration) {
  const start = performance.now();
  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3); // ease-out-cubic
    el.textContent = Math.round(from + (to - from) * eased);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// ─── Section Switching ────────────────────────────────────────────────────────
function showSection(which) {
  D.sectionUpload.classList.toggle('hidden', which !== 'upload');
  D.sectionProcessing.classList.toggle('hidden', which !== 'processing');
  D.sectionResult.classList.toggle('hidden', which !== 'result');
}

// ─── Reset ────────────────────────────────────────────────────────────────────
D.btnReset.addEventListener('click', () => {
  clearFile();
  D.jdUrl.value = '';
  D.jdText.value = '';
  state.sessionId = null;
  clearAllSteps();
  D.gaugeScore.textContent = '0';
  D.scoreArc.setAttribute('stroke-dasharray', '0 502');
  showSection('upload');
});

// ─── Error Toast ──────────────────────────────────────────────────────────────
let errorTimer = null;

function showError(msg) {
  D.errorMessage.textContent = msg;
  D.errorToast.classList.remove('hidden');
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(() => D.errorToast.classList.add('hidden'), 6000);
}

D.errorClose.addEventListener('click', () => {
  D.errorToast.classList.add('hidden');
  if (errorTimer) clearTimeout(errorTimer);
});

// ─── Utilities ────────────────────────────────────────────────────────────────
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── Init ─────────────────────────────────────────────────────────────────────
updateSubmitState();
showSection('upload');
