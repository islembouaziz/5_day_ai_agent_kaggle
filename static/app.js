/**
 * CV Job Matcher — Frontend Application Logic
 * Handles: drag-and-drop upload, API calls, results rendering
 */

// ── DOM REFERENCES ─────────────────────────────────────────────────────────
const dropZone       = document.getElementById('drop-zone');
const fileInput      = document.getElementById('file-input');
const browseBtn      = document.getElementById('browse-btn');
const fileSelected   = document.getElementById('file-selected');
const fileNameEl     = document.getElementById('file-name');
const fileSizeEl     = document.getElementById('file-size');
const removeBtn      = document.getElementById('remove-btn');
const analyzeBtn     = document.getElementById('analyze-btn');

const heroSection    = document.getElementById('hero');
const uploadSection  = document.getElementById('upload-section');
const loadingSection = document.getElementById('loading-section');
const loadingStatus  = document.getElementById('loading-status');
const resultsSection = document.getElementById('results-section');

const cvSummaryText  = document.getElementById('cv-summary-text');
const statJobs       = document.getElementById('stat-jobs');
const statTopScore   = document.getElementById('stat-top-score');
const statSkills     = document.getElementById('stat-skills');
const jobsList       = document.getElementById('jobs-list');
const suggestionsList = document.getElementById('suggestions-list');
const skillsGrid     = document.getElementById('skills-grid');
const newAnalysisBtn = document.getElementById('new-analysis-btn');

const errorToast     = document.getElementById('error-toast');
const errorMessage   = document.getElementById('error-message');
const errorClose     = document.getElementById('error-close');

const steps          = [1,2,3,4].map(i => document.getElementById(`step-${i}`));

// ── STATE ──────────────────────────────────────────────────────────────────
let selectedFile = null;

// ── DRAG & DROP ────────────────────────────────────────────────────────────
dropZone.addEventListener('dragenter', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', (e) => {
  if (!dropZone.contains(e.relatedTarget)) {
    dropZone.classList.remove('drag-over');
  }
});
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) handleFileSelection(files[0]);
});

// Click on drop zone (but not browse button or input itself) opens file picker
dropZone.addEventListener('click', (e) => {
  if (e.target !== browseBtn && e.target !== fileInput) fileInput.click();
});

// Keyboard accessibility for drop zone
dropZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) handleFileSelection(fileInput.files[0]);
});

// ── FILE SELECTION ─────────────────────────────────────────────────────────
function handleFileSelection(file) {
  const name = file.name.toLowerCase();
  if (!name.endsWith('.pdf') && !name.endsWith('.html')) {
    showError('Please upload a PDF or HTML file.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError('File is too large. Maximum size is 10 MB.');
    return;
  }

  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = formatBytes(file.size);

  dropZone.hidden = true;
  fileSelected.hidden = false;
  analyzeBtn.disabled = false;
}

removeBtn.addEventListener('click', resetUpload);

function resetUpload() {
  selectedFile = null;
  fileInput.value = '';
  dropZone.hidden = false;
  fileSelected.hidden = true;
  analyzeBtn.disabled = true;
  analyzeBtn.classList.remove('loading');
  analyzeBtn.querySelector('.btn-text').textContent = 'Analyze My CV';
}

// ── ANALYZE ────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', startAnalysis);

async function startAnalysis() {
  if (!selectedFile) return;

  // Prevent double click double upload
  analyzeBtn.disabled = true;

  // UI: show loading
  hideAll();
  loadingSection.hidden = false;
  resetLoadingSteps();
  setLoadingStep(1);

  const formData = new FormData();
  formData.append('file', selectedFile);

  // Simulate step progression while the server processes
  const stepTimers = [
    setTimeout(() => setLoadingStep(2), 3000),
    setTimeout(() => setLoadingStep(3), 8000),
    setTimeout(() => setLoadingStep(4), 15000),
  ];

  try {
    setStatus('Fetching live job listings...');

    const response = await fetch('/analyze', {
      method: 'POST',
      body: formData,
    });

    stepTimers.forEach(t => clearTimeout(t));

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown server error.' }));
      throw new Error(errorData.detail || `Server error ${response.status}`);
    }

    const data = await response.json();

    // Mark all steps done
    steps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
    await sleep(500);

    renderResults(data);
  } catch (err) {
    stepTimers.forEach(t => clearTimeout(t));
    loadingSection.hidden = true;
    heroSection.hidden = false;

    showError(
      err.message.includes('Failed to fetch')
        ? 'Cannot connect to the server. Make sure the app is running (uvicorn main:app --reload).'
        : err.message
    );

    resetUpload();
  }
}

// ── RENDER RESULTS ─────────────────────────────────────────────────────────
function renderResults(data) {
  loadingSection.hidden = true;
  resultsSection.hidden = false;

  // CV Summary
  cvSummaryText.textContent = data.cv_summary || 'Analysis complete.';

  // Stats
  const jobs = data.matched_jobs || [];
  const topScore = jobs.length > 0 ? jobs[0].match_score : 0;
  const skillCount = (data.top_missing_skills || []).length;

  animateCount(statJobs, 0, jobs.length, 600);
  setTimeout(() => animateCount(statTopScore, 0, topScore, 800, '%'), 200);
  setTimeout(() => animateCount(statSkills, 0, skillCount, 600), 400);

  // Job cards
  jobsList.innerHTML = '';
  if (jobs.length === 0) {
    jobsList.innerHTML = `
      <div class="job-card" style="text-align:center; padding: 40px;">
        <p style="font-size: 32px; margin-bottom: 12px;">🔍</p>
        <p style="color: var(--text-secondary);">No strong matches found. Try uploading a different CV or check your preferences.</p>
      </div>`;
  } else {
    jobs.forEach((job, i) => {
      const card = buildJobCard(job, i);
      jobsList.appendChild(card);
    });
  }

  // Global Suggestions
  suggestionsList.innerHTML = '';
  (data.global_suggestions || []).forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'suggestion-item';
    li.style.animationDelay = `${i * 0.08}s`;
    li.innerHTML = `<span class="suggestion-num">${i + 1}</span><span>${escapeHtml(s)}</span>`;
    suggestionsList.appendChild(li);
  });

  // Skills Grid
  skillsGrid.innerHTML = '';
  (data.top_missing_skills || []).forEach((skill, i) => {
    const chip = document.createElement('div');
    chip.className = 'skill-chip';
    chip.style.animationDelay = `${i * 0.06}s`;
    chip.textContent = skill;
    skillsGrid.appendChild(chip);
  });

  // Scroll to results
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildJobCard(job, index) {
  const card = document.createElement('article');
  card.className = 'job-card';
  card.setAttribute('role', 'listitem');
  card.style.animationDelay = `${index * 0.06}s`;

  const scoreClass = job.match_score >= 70 ? 'high' : job.match_score >= 50 ? 'medium' : 'low';

  const metaTags = [
    job.location ? `<span class="meta-tag location">📍 ${escapeHtml(job.location)}</span>` : '',
    job.remote ? `<span class="meta-tag remote">🌐 Remote</span>` : '',
    ...(job.job_types || []).map(t => `<span class="meta-tag type">${escapeHtml(t)}</span>`),
    ...(job.tags || []).slice(0, 2).map(t => `<span class="meta-tag tag">${escapeHtml(t)}</span>`),
  ].filter(Boolean).join('');

  const reasonsHtml = (job.match_reasons || []).map(r =>
    `<div class="reason-item">${escapeHtml(r)}</div>`
  ).join('');

  const missingHtml = (job.missing_skills || []).map(s =>
    `<div class="missing-item">${escapeHtml(s)}</div>`
  ).join('');

  card.innerHTML = `
    <div class="job-card-header">
      <div class="job-title-group">
        <div class="job-title">${escapeHtml(job.title)}</div>
        <div class="job-company">${escapeHtml(job.company_name)}</div>
      </div>
      <div class="score-badge">
        <div class="score-ring ${scoreClass}" aria-label="Match score ${job.match_score} out of 100">
          ${job.match_score}
        </div>
        <div class="score-label">match</div>
      </div>
    </div>

    <div class="job-meta">${metaTags}</div>

    ${reasonsHtml ? `
    <div class="match-reasons">
      <div class="reasons-title">✓ Why it fits</div>
      ${reasonsHtml}
    </div>` : ''}

    ${missingHtml ? `
    <div class="missing-skills">
      <div class="missing-title">→ Missing skills</div>
      ${missingHtml}
    </div>` : ''}

    <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" class="apply-link" id="apply-${escapeHtml(job.slug)}">
      View Job ↗
    </a>
  `;

  return card;
}

// ── NEW ANALYSIS ───────────────────────────────────────────────────────────
newAnalysisBtn.addEventListener('click', () => {
  resultsSection.hidden = true;
  heroSection.hidden = false;
  resetUpload();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ── LOADING STEPS ──────────────────────────────────────────────────────────
const stepMessages = [
  'Fetching live job listings...',
  'Parsing your CV...',
  'AI matching jobs to your profile...',
  'Generating improvement suggestions...',
];

function resetLoadingSteps() {
  steps.forEach(s => {
    s.classList.remove('active', 'done');
  });
}

function setLoadingStep(stepNum) {
  steps.forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i < stepNum - 1) s.classList.add('done');
    else if (i === stepNum - 1) s.classList.add('active');
  });
  setStatus(stepMessages[stepNum - 1] || 'Processing...');
}

function setStatus(msg) {
  loadingStatus.textContent = msg;
}

// ── ERROR TOAST ────────────────────────────────────────────────────────────
function showError(msg) {
  errorMessage.textContent = msg;
  errorToast.hidden = false;
  setTimeout(() => { errorToast.hidden = true; }, 8000);
}

errorClose.addEventListener('click', () => { errorToast.hidden = true; });

// ── HELPERS ────────────────────────────────────────────────────────────────
function hideAll() {
  heroSection.hidden = true;
  loadingSection.hidden = true;
  resultsSection.hidden = true;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function animateCount(el, from, to, duration, suffix = '') {
  const start = performance.now();
  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = Math.round(from + (to - from) * ease);
    el.textContent = current + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}
