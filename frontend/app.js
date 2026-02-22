/**
 * ResumeAI · Frontend Application Logic
 * State machine: UPLOAD → PROCESSING → RESULT
 */

'use strict';

const API_BASE = '';
const MAX_FILE_MB = 10;

const STEP_MESSAGES = [
  'Extracting job requirements...',
  'Analyzing resume structure...',
  'Identifying skill gaps via AI...',
  'Generating optimization suggestions...',
  'Calculating final ATS score...',
];

let state = {
  file: null,
  sessionId: null,
  activeTab: 'url',
  isProcessing: false,
};

const $ = (id) => document.getElementById(id);

const D = {
  dropzone: $('dropzone'),
  fileInput: $('fileInput'),
  filePreview: $('filePreview'),
  fileName: $('fileName'),
  fileSize: $('fileSize'),
  fileTypeIcon: $('fileTypeIcon'),
  fileRemove: $('fileRemove'),
  tabUrl: $('tab-url'),
  tabPaste: $('tab-paste'),
  jdUrlPanel: $('jd-url-panel'),
  jdPastePanel: $('jd-paste-panel'),
  jdUrl: $('jdUrl'),
  jdText: $('jdText'),
  btnOptimize: $('btnOptimize'),
  submitHint: $('submitHint'),

  sectionUpload: $('section-upload'),
  sectionProcessing: $('section-processing'),
  sectionResult: $('section-result'),
  processingStep: $('processingStep'),

  resultJobTitle: $('resultJobTitle'),
  gaugeScore: $('gaugeScore'),
  scoreArc: $('scoreArc'),
  scoreKeyword: $('scoreKeyword'),
  scoreRelevancy: $('scoreRelevancy'),
  scoreFormat: $('scoreFormat'),
  barKeyword: $('barKeyword'),
  barRelevancy: $('barRelevancy'),
  barFormat: $('barFormat'),
  resultFeedback: $('resultFeedback'),
  matchedKeywords: $('matchedKeywords'),
  missingKeywords: $('missingKeywords'),
  sectionsFound: $('sectionsFound'),
  btnReset: $('btnReset'),
  prospectiveBadge: $('prospectiveBadge'),
  prospectiveScore: $('prospectiveScore'),

  analysisMissingSkills: $('analysisMissingSkills'),
  summarySuggestionsList: $('summarySuggestionsList'),
  experienceSuggestionsList: $('experienceSuggestionsList'),

  errorToast: $('errorToast'),
  errorMessage: $('errorMessage'),
  errorClose: $('errorClose'),
};

// --- File Handling ---
D.dropzone.addEventListener('click', (e) => {
  // If the user clicked the label or the input itself, don't trigger another click
  if (e.target.tagName === 'LABEL' || e.target.tagName === 'INPUT') return;

  console.log('[DEBUG] Dropzone clicked');
  D.fileInput.click();
});

D.fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  console.log('[DEBUG] fileInput change event:', file ? file.name : 'no file');
  if (file) setFile(file);
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
  console.log('[DEBUG] file dropped:', file ? file.name : 'no file');
  if (file) setFile(file);
});
D.fileRemove.addEventListener('click', clearFile);

function setFile(file) {
  console.log('[DEBUG] Setting file:', file.name);
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    showError('Please upload a PDF or DOCX file.');
    return;
  }
  state.file = file;
  D.fileName.textContent = file.name;
  D.fileSize.textContent = formatBytes(file.size);
  D.fileTypeIcon.textContent = ext === 'pdf' ? '📄' : '📝';
  D.filePreview.classList.remove('hidden');
  D.dropzone.classList.add('hidden');

  // CRITICAL FIX: Reset input value so selecting the same file again triggers 'change' event
  D.fileInput.value = '';

  updateSubmitState();
}

function clearFile() {
  console.log('[DEBUG] Clearing file');
  state.file = null;
  D.fileInput.value = '';
  D.filePreview.classList.add('hidden');
  D.dropzone.classList.remove('hidden');
  updateSubmitState();
}

// --- JD Tabs ---
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

function updateSubmitState() {
  const hasFile = !!state.file;
  const hasJd = (state.activeTab === 'url' && D.jdUrl.value.trim().length > 5) ||
    (state.activeTab === 'paste' && D.jdText.value.trim().length > 30);

  const canSubmit = hasFile && hasJd && !state.isProcessing;
  D.btnOptimize.disabled = !canSubmit;

  console.log('[DEBUG] state updated:', { hasFile, hasJd, isProcessing: state.isProcessing, canSubmit });

  D.submitHint.textContent = !hasFile
    ? 'Upload a resume to get started'
    : !hasJd
      ? 'Add a job description to continue'
      : state.isProcessing
        ? 'Processing analysis...'
        : 'Ready for analysis!';
}

// --- Submit Logic ---
D.btnOptimize.addEventListener('click', startOptimize);

async function startOptimize() {
  if (!state.file || state.isProcessing) {
    console.warn('[DEBUG] startOptimize skipped:', { file: !!state.file, isProcessing: state.isProcessing });
    return;
  }

  console.log('[DEBUG] Starting optimization pipeline...');
  state.isProcessing = true;
  updateSubmitState();

  showSection('processing');
  animateSteps();

  const formData = new FormData();
  formData.append('file', state.file);
  if (state.activeTab === 'url' && D.jdUrl.value.trim()) formData.append('jd_url', D.jdUrl.value.trim());
  if (D.jdText.value.trim()) formData.append('jd_text', D.jdText.value.trim());

  try {
    const res = await fetch(`${API_BASE}/api/optimize`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Network error or timeout' }));
      throw new Error(err.detail || 'Analysis failed');
    }
    const data = await res.json();
    console.log('[DEBUG] Analysis complete:', data);
    await sleep(800);
    showResults(data);
  } catch (err) {
    console.error('[ERROR] Optimization failed:', err);
    showSection('upload');
    showError(err.message || 'Analysis failed. Please try again.');
  } finally {
    state.isProcessing = false;
    updateSubmitState();
  }
}

function showResults(data) {
  const score = data.ats_score || {};
  const analysis = data.analysis || {};

  for (let i = 1; i <= 5; i++) markStepDone(i);
  showSection('result');

  D.resultJobTitle.textContent = data.job_title || 'Analysis Result';
  D.resultFeedback.textContent = score.feedback || 'Analysis complete.';

  const total = score.total || 0;
  animateCounter(D.gaugeScore, 0, total, 1000);

  if (score.prospective_score) {
    D.prospectiveBadge.classList.remove('hidden');
    animateCounter(D.prospectiveScore, 0, score.prospective_score, 1200);
  } else {
    D.prospectiveBadge.classList.add('hidden');
  }
  const circ = 502;
  const fill = (total / 100) * circ;
  D.scoreArc.setAttribute('stroke-dasharray', `${fill} ${circ - fill}`);

  D.scoreKeyword.textContent = `${score.keyword_match || 0}/40`;
  D.scoreRelevancy.textContent = `${score.role_relevancy || 0}/40`;
  D.scoreFormat.textContent = `${score.formatting_simplicity || 0}/20`;
  D.barKeyword.style.width = `${((score.keyword_match || 0) / 40) * 100}%`;
  D.barRelevancy.style.width = `${((score.role_relevancy || 0) / 40) * 100}%`;
  D.barFormat.style.width = `${((score.formatting_simplicity || 0) / 20) * 100}%`;

  renderKeywordTags(D.matchedKeywords, score.top_matched_keywords, 'keyword-tag');
  renderKeywordTags(D.missingKeywords, score.missing_keywords, 'keyword-tag');

  renderKeywordTags(D.analysisMissingSkills, analysis.missing_skills, 'keyword-tag');
  renderSuggestions(D.summarySuggestionsList, analysis.summary_suggestions);
  renderSuggestions(D.experienceSuggestionsList, analysis.experience_suggestions);

  const total_found = (data.sections_found?.summary_blocks || 0) + (data.sections_found?.experience_blocks || 0);
  D.sectionsFound.textContent = `${total_found} blocks analyzed`;
}

function renderSuggestions(container, suggestions) {
  container.innerHTML = '';
  if (!suggestions || suggestions.length === 0) {
    container.innerHTML = '<p class="suggest-text" style="color:var(--text-muted)">No specific suggestions for this section.</p>';
    return;
  }
  suggestions.forEach(s => {
    const item = document.createElement('div');
    item.className = 'suggestion-item';
    item.innerHTML = `
      <div class="suggest-original">
        <span class="suggest-label">Original</span>
        <p class="suggest-text">${s.original}</p>
      </div>
      <div class="suggest-modified">
        <span class="suggest-label">Suggested Optimization</span>
        <p class="suggest-text">${s.suggested}</p>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderKeywordTags(container, keywords, className) {
  container.innerHTML = '';
  (keywords || []).forEach(kw => {
    const tag = document.createElement('span');
    tag.className = className;
    tag.textContent = kw;
    container.appendChild(tag);
  });
}

function showSection(which) {
  D.sectionUpload.classList.toggle('hidden', which !== 'upload');
  D.sectionProcessing.classList.toggle('hidden', which !== 'processing');
  D.sectionResult.classList.toggle('hidden', which !== 'result');
}

let animInterval = null;
function animateSteps() {
  if (animInterval) clearInterval(animInterval);
  let step = 1;
  D.processingStep.textContent = STEP_MESSAGES[0];
  markStepActive(1);
  animInterval = setInterval(() => {
    markStepDone(step);
    step++;
    if (step > 5) { clearInterval(animInterval); return; }
    markStepActive(step);
    D.processingStep.textContent = STEP_MESSAGES[step - 1];
  }, 1800);
}

function markStepActive(n) { const el = $(`step-${n}`); if (el) el.classList.add('active'); }
function markStepDone(n) { const el = $(`step-${n}`); if (el) { el.classList.remove('active'); el.classList.add('done'); } }

function animateCounter(el, from, to, duration) {
  const start = performance.now();
  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(from + (to - from) * t);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function showError(msg) {
  D.errorMessage.textContent = msg;
  D.errorToast.classList.remove('hidden');
  setTimeout(() => D.errorToast.classList.add('hidden'), 5000);
}

D.btnReset.addEventListener('click', () => {
  clearFile();
  D.jdUrl.value = '';
  D.jdText.value = '';
  D.prospectiveBadge.classList.add('hidden');
  showSection('upload');
});
