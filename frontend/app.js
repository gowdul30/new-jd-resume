/**
 * ResumeAI · Frontend Application Logic (Refactored for Dark Mode & Documents)
 */
'use strict';

console.log('ResumeAI: app.js loaded');

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

const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`ResumeAI: Element with id "${id}" not found.`);
  return el;
};

document.addEventListener('DOMContentLoaded', () => {
  console.log('ResumeAI: DOM fully loaded');

  const D = {
    themeToggle: $('themeToggle'),
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

    sectionHero: $('section-hero'),
    trustFactors: $('trust-factors'),
    sectionUpload: $('section-upload'),
    sectionProcessing: $('section-processing'),
    sectionResult: $('section-result'),
    processingStep: $('processingStep'),

    resultJobTitle: $('resultJobTitle'),
    gaugeScore: $('gaugeScore'),
    scoreArc: $('scoreArc'),
    resultFeedback: $('resultFeedback'),
    btnReset: $('btnReset'),

    originalPreview: $('originalPreview'),
    optimizedPreview: $('optimizedPreview'),

    errorToast: $('errorToast'),
    errorMessage: $('errorMessage'),
    errorClose: $('errorClose'),
  };

  // Dark mode toggle
  if (D.themeToggle) {
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    D.themeToggle.addEventListener('click', () => {
      console.log('ResumeAI: Theme toggle clicked');
      document.documentElement.classList.toggle('dark');
      if (document.documentElement.classList.contains('dark')) {
        localStorage.theme = 'dark';
      } else {
        localStorage.theme = 'light';
      }
    });
  }

  // --- File Handling ---
  if (D.dropzone) {
    D.dropzone.addEventListener('click', (e) => {
      console.log('ResumeAI: Dropzone clicked');
      // If we clicked directly on the input if it was visible, or a label, don't trigger again
      if (e.target.tagName === 'LABEL' || e.target.tagName === 'INPUT') return;
      if (D.fileInput) D.fileInput.click();
    });

    D.dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      D.dropzone.classList.add('border-brand');
    });
    D.dropzone.addEventListener('dragleave', () => D.dropzone.classList.remove('border-brand'));
    D.dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      D.dropzone.classList.remove('border-brand');
      const file = e.dataTransfer.files[0];
      if (file) setFile(file);
    });
  }

  if (D.fileInput) {
    D.fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) setFile(file);
    });
  }

  if (D.fileRemove) {
    D.fileRemove.addEventListener('click', (e) => {
      e.stopPropagation();
      clearFile();
    });
  }

  function setFile(file) {
    console.log('ResumeAI: File set', file.name);
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      showError('Please upload a PDF or DOCX file.');
      return;
    }
    state.file = file;
    if (D.fileName) D.fileName.textContent = file.name;
    if (D.fileSize) D.fileSize.textContent = formatBytes(file.size);
    if (D.fileTypeIcon) D.fileTypeIcon.textContent = ext === 'pdf' ? '📄' : '📝';
    if (D.filePreview) D.filePreview.classList.remove('hidden');
    if (D.dropzone) D.dropzone.classList.add('hidden');
    if (D.fileInput) D.fileInput.value = '';
    updateSubmitState();
  }

  function clearFile() {
    console.log('ResumeAI: File cleared');
    state.file = null;
    if (D.fileInput) D.fileInput.value = '';
    if (D.filePreview) D.filePreview.classList.add('hidden');
    if (D.dropzone) D.dropzone.classList.remove('hidden');
    updateSubmitState();
  }

  // --- JD Tabs ---
  [D.tabUrl, D.tabPaste].forEach((tab) => {
    if (tab) {
      tab.addEventListener('click', () => {
        const which = tab.dataset.tab;
        console.log('ResumeAI: JD Tab switched to', which);
        state.activeTab = which;

        if (which === 'url') {
          if (D.tabUrl) D.tabUrl.className = "flex-1 py-2 text-sm font-medium rounded-lg bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white transition-all";
          if (D.tabPaste) D.tabPaste.className = "flex-1 py-2 text-sm font-medium rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white transition-all";
        } else {
          if (D.tabUrl) D.tabUrl.className = "flex-1 py-2 text-sm font-medium rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white transition-all";
          if (D.tabPaste) D.tabPaste.className = "flex-1 py-2 text-sm font-medium rounded-lg bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white transition-all";
        }

        if (D.jdUrlPanel) D.jdUrlPanel.classList.toggle('hidden', which !== 'url');
        if (D.jdPastePanel) D.jdPastePanel.classList.toggle('hidden', which !== 'paste');
        updateSubmitState();
      });
    }
  });

  if (D.jdUrl) D.jdUrl.addEventListener('input', updateSubmitState);
  if (D.jdText) D.jdText.addEventListener('input', updateSubmitState);

  function updateSubmitState() {
    const hasFile = !!state.file;
    const hasJd = (state.activeTab === 'url' && D.jdUrl && D.jdUrl.value.trim().length > 5) ||
      (state.activeTab === 'paste' && D.jdText && D.jdText.value.trim().length > 30);

    const canSubmit = hasFile && hasJd && !state.isProcessing;
    if (D.btnOptimize) D.btnOptimize.disabled = !canSubmit;

    if (D.submitHint) {
      D.submitHint.textContent = !hasFile
        ? 'Upload a resume to get started'
        : !hasJd
          ? 'Add a job description to continue'
          : state.isProcessing
            ? 'Processing analysis...'
            : 'Ready for analysis!';
    }
  }

  // --- Submit Logic ---
  if (D.btnOptimize) {
    D.btnOptimize.addEventListener('click', startOptimize);
  }

  async function startOptimize() {
    if (!state.file || state.isProcessing) return;

    console.log('ResumeAI: Starting optimization...');
    state.isProcessing = true;
    updateSubmitState();

    showSection('processing');
    animateSteps();

    const formData = new FormData();
    formData.append('file', state.file);
    if (state.activeTab === 'url' && D.jdUrl && D.jdUrl.value.trim()) formData.append('jd_url', D.jdUrl.value.trim());
    if (D.jdText && D.jdText.value.trim()) formData.append('jd_text', D.jdText.value.trim());

    try {
      const res = await fetch(`${API_BASE}/api/optimize`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Network error or timeout' }));
        throw new Error(err.detail || 'Analysis failed');
      }
      const data = await res.json();
      await sleep(800);
      showResults(data);
    } catch (err) {
      console.error('ResumeAI: Optimization failed', err);
      showSection('upload');
      showError(err.message || 'Analysis failed. Please try again.');
    } finally {
      state.isProcessing = false;
      updateSubmitState();
    }
  }

  function showResults(data) {
    console.log('ResumeAI: Showing results', data);
    const score = data.ats_score || {};
    const analysis = data.analysis || {};

    for (let i = 1; i <= 5; i++) markStepDone(i);
    showSection('result');

    if (D.resultJobTitle) D.resultJobTitle.textContent = data.job_title || 'Software Engineer · Analyzed';
    if (D.resultFeedback) D.resultFeedback.textContent = score.feedback || 'Your resume has been deeply analyzed and optimized based on the provided job description requirements.';

    const total = score.total || 0;
    if (D.gaugeScore) animateCounter(D.gaugeScore, 0, total, 1000);

    let gaugeColor = 'text-brand';
    if (total >= 40 && total < 75) gaugeColor = 'text-orange-500';
    if (total >= 75) gaugeColor = 'text-emerald-500';

    if (D.scoreArc) {
      D.scoreArc.className.baseVal = `progress-circle stroke-current ${gaugeColor}`;
      const circ = 282.7;
      const offset = circ - (total / 100) * circ;
      D.scoreArc.setAttribute('stroke-dashoffset', offset);
    }

    // --- Modern Comparison Widgets ---
    // --- Modern Comparison Widgets ---
    // (Keyword Alignment removed)

    // 2. Skills Comparison (Existing vs Missing)
    const existingSWrap = $('existingSkillsContainer');
    const missingSWrap = $('missingSkillsContainer');
    if (existingSWrap) {
      existingSWrap.innerHTML = (analysis.existing_skills || []).map(skill =>
        `<span class="px-2 py-1 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20 font-medium">${skill}</span>`
      ).join('') || '<span class="text-slate-500 italic">No skills extracted</span>';
    }
    if (missingSWrap) {
      missingSWrap.innerHTML = (analysis.missing_skills || []).map(skill =>
        `<span class="px-2 py-1 rounded bg-brand/10 text-brand border border-brand/20 font-medium">${skill}</span>`
      ).join('') || '<span class="text-emerald-500 italic">✓ No missing skills found</span>';
    }

    // 3. Summary Optimization Comparison
    const summaryWrap = $('summarySuggestionsContainer');
    if (summaryWrap && analysis.summary_suggestions) {
      summaryWrap.innerHTML = analysis.summary_suggestions.map(s => `
        <div class="glassmorphism rounded-xl p-5 border dark:border-slate-800 flex flex-col gap-4">
           <div class="space-y-2">
              <p class="text-[10px] font-bold text-indigo-500 uppercase tracking-widest flex items-center gap-2">
                 <span class="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span> Optimized Summary
              </p>
              <p class="text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-medium bg-indigo-500/5 p-3 rounded-lg border border-indigo-500/10">${s.suggested || s}</p>
           </div>
        </div>
      `).join('') || '<p class="text-center text-slate-500 italic">No summary optimizations needed.</p>';
    }

    // 4. Experience Comparisons (Comparative View)
    const expSuggestionsWrap = $('experienceSuggestionsContainer');
    if (expSuggestionsWrap && analysis.experience_suggestions) {
      if (analysis.experience_suggestions.length > 0) {
        expSuggestionsWrap.innerHTML = analysis.experience_suggestions.map(s => `
          <div class="glassmorphism rounded-xl p-5 border dark:border-slate-800 flex flex-col gap-4">
             <div class="space-y-2">
                <p class="text-[10px] font-bold text-cyan-500 uppercase tracking-widest flex items-center gap-2">
                   <span class="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse"></span> Suggested Optimization
                </p>
                <p class="text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-medium bg-cyan-500/5 p-3 rounded-lg border border-cyan-500/10">"${s.suggested || s}"</p>
             </div>
          </div>
        `).join('');
      } else {
        expSuggestionsWrap.innerHTML = `<p class="text-center text-slate-500 italic py-8">Your bullet points are already highly optimized.</p>`;
      }
    }
  }

  function buildDocumentHTML(analysis, isOptimized) {
    let name = "[Candidate Name]";
    let contact = "email@example.com | (555) 123-4567 | linkedin.com/in/candidate";

    let summaries = (analysis.summary_suggestions || []).map(s => isOptimized ? s.suggested : s.original);
    if (summaries.length === 0) summaries = [isOptimized ? "Highly optimized professional summary leveraging key requirements from the job description to demonstrate immediate impact. Eager to bring track record of excellence to the new team." : "Professional summary describing generic skills and past experiences."];

    let experiences = (analysis.experience_suggestions || []).map(s => isOptimized ? s.suggested : s.original);
    if (experiences.length === 0) experiences = [
      isOptimized ? "• Engineered a scalable microservices architecture reducing server load by 40%." : "• Worked on server architecture and improved performance.",
      isOptimized ? "• Led cross-functional team of 5 to deliver critical MVP 2 weeks ahead of schedule." : "• Managed a team to build an MVP."
    ];

    let skills = (analysis.missing_skills || []).join(", ");
    if (!skills) skills = "Python, AWS, React, Docker, SQL";

    return `
      <div style="font-family: inherit">
          <h1 class="text-3xl font-bold mb-2 text-center uppercase border-b-2 border-slate-300 pb-2">${name}</h1>
          <p class="text-center mb-6 text-slate-500">${contact}</p>
          
          <h2 class="text-xl font-bold uppercase mb-2 ${isOptimized ? 'text-brand' : ''}">Professional Summary</h2>
          <p class="mb-6 text-justify">${summaries.join(" ")}</p>
  
          <h2 class="text-xl font-bold uppercase mb-2 ${isOptimized ? 'text-brand' : ''}">Professional Experience</h2>
          <div class="mb-4">
              <div class="flex justify-between font-bold">
                  <span>Senior Software Engineer</span>
                  <span>Tech Corp Inc. | 2020 - Present</span>
              </div>
              <ul class="list-disc pl-5 mt-2 space-y-2">
                  ${experiences.map(e => `<li>${e}</li>`).join('')}
              </ul>
          </div>
          
          <h2 class="text-xl font-bold uppercase mb-2 ${isOptimized ? 'text-brand' : ''}">Core Competencies</h2>
          <p class="mb-6 text-justify">${isOptimized ? skills + ', Agile, Leadership' : 'Basic programming, teamwork'}</p>
      </div>
    `;
  }

  function populateDocumentPreview(container, html) {
    container.innerHTML = html;
  }

  function showSection(which) {
    if (D.sectionHero) D.sectionHero.classList.toggle('hidden', which !== 'upload');
    if (D.trustFactors) D.trustFactors.classList.toggle('hidden', which !== 'upload');
    if (D.sectionUpload) D.sectionUpload.classList.toggle('hidden', which !== 'upload');

    if (D.sectionProcessing) D.sectionProcessing.classList.toggle('hidden', which !== 'processing');
    if (D.sectionResult) D.sectionResult.classList.toggle('hidden', which !== 'result');
  }

  let animInterval = null;
  function animateSteps() {
    if (animInterval) clearInterval(animInterval);
    let step = 1;
    if (D.processingStep) D.processingStep.textContent = STEP_MESSAGES[0];
    markStepActive(1);
    animInterval = setInterval(() => {
      markStepDone(step);
      step++;
      if (step > 5) { clearInterval(animInterval); return; }
      markStepActive(step);
      if (D.processingStep) D.processingStep.textContent = STEP_MESSAGES[step - 1];
    }, 1800);
  }

  function markStepActive(n) {
    const el = $(`step-${n}`);
    if (el) {
      const ind = el.querySelector('.step-indicator');
      if (ind) ind.classList.add('bg-brand', 'animate-pulse');
      el.classList.add('text-slate-900', 'dark:text-white', 'font-medium');
    }
  }
  function markStepDone(n) {
    const el = $(`step-${n}`);
    if (el) {
      const ind = el.querySelector('.step-indicator');
      if (ind) {
        ind.classList.remove('bg-brand', 'animate-pulse');
        ind.classList.add('bg-emerald-500');
      }
      el.classList.remove('text-slate-900', 'dark:text-white', 'font-medium');
      el.classList.add('text-emerald-600', 'dark:text-emerald-500');
    }
  }

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
    if (D.errorMessage) D.errorMessage.textContent = msg;
    if (D.errorToast) {
      D.errorToast.classList.remove('hidden');
      D.errorToast.classList.add('opacity-100');
      setTimeout(() => {
        D.errorToast.classList.add('hidden');
      }, 5000);
    }
  }

  if (D.errorClose) {
    D.errorClose.addEventListener('click', () => {
      if (D.errorToast) D.errorToast.classList.add('hidden');
    });
  }

  if (D.btnReset) {
    D.btnReset.addEventListener('click', () => {
      clearFile();
      if (D.jdUrl) D.jdUrl.value = '';
      if (D.jdText) D.jdText.value = '';
      const prContainer = $('prospective-container');
      if (prContainer) prContainer.classList.add('hidden');

      // Reset comparison containers
      const containers = ['existingSkillsContainer', 'missingSkillsContainer', 'summarySuggestionsContainer', 'experienceSuggestionsContainer'];
      containers.forEach(id => {
        const el = $(id);
        if (el) el.innerHTML = '<span class="text-slate-500 italic">Analyzing...</span>';
      });

      showSection('upload');
    });
  }
});
