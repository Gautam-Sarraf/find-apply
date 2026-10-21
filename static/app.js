/**
 * RemoteJobPulse - Client Application Logic with AI Resume Matcher
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    query: '',
    provider: 'all',
    salaryOnly: false,
    sortBy: 'default',
    page: 1,
    pageSize: 24,
    totalJobs: 0,
    totalPages: 1,
    jobs: [],
    selectedJob: null,

    // Resume Matching State
    isMatchingMode: false,
    candidateProfile: null,
    selectedFile: null,
    pastedText: '',
    matchedJobs: []
  };

  // DOM Elements - Main Controls
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const providerChips = document.querySelectorAll('#providerFilterGroup .chip');
  const salaryToggle = document.getElementById('salaryToggle');
  const sortSelect = document.getElementById('sortSelect');
  const optSortMatch = document.getElementById('optSortMatch');
  const optSortDefault = document.getElementById('optSortDefault');
  const jobsContainer = document.getElementById('jobsContainer');
  const resultsCount = document.getElementById('resultsCount');
  const activeQueryBadge = document.getElementById('activeQueryBadge');
  const emptyState = document.getElementById('emptyState');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const spinIcon = refreshBtn ? refreshBtn.querySelector('.spin-icon') : null;

  // View Switcher Tabs
  const tabBrowseJobs = document.getElementById('tabBrowseJobs');
  const tabResumeMatch = document.getElementById('tabResumeMatch');

  // Candidate Profile Ribbon Elements
  const candidateRibbon = document.getElementById('candidateRibbon');
  const ribbonAvatar = document.getElementById('ribbonAvatar');
  const ribbonName = document.getElementById('ribbonName');
  const ribbonExpBadge = document.getElementById('ribbonExpBadge');
  const ribbonRole = document.getElementById('ribbonRole');
  const ribbonSkillsList = document.getElementById('ribbonSkillsList');
  const reuploadResumeBtn = document.getElementById('reuploadResumeBtn');
  const clearResumeBtn = document.getElementById('clearResumeBtn');

  // Stats Elements
  const statTotalJobs = document.getElementById('statTotalJobs');
  const statSalaryCount = document.getElementById('statSalaryCount');
  const statLastSync = document.getElementById('statLastSync');
  const statCacheAge = document.getElementById('statCacheAge');

  // Pagination Elements
  const paginationContainer = document.getElementById('paginationContainer');
  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const pageIndicator = document.getElementById('pageIndicator');

  // Resume Upload Modal Elements
  const headerResumeBtn = document.getElementById('headerResumeBtn');
  const resumeUploadModal = document.getElementById('resumeUploadModal');
  const resumeModalCloseBtn = document.getElementById('resumeModalCloseBtn');
  const cancelResumeBtn = document.getElementById('cancelResumeBtn');
  const startMatchBtn = document.getElementById('startMatchBtn');
  const tabUploadFile = document.getElementById('tabUploadFile');
  const tabPasteText = document.getElementById('tabPasteText');
  const fileUploadSection = document.getElementById('fileUploadSection');
  const pasteTextSection = document.getElementById('pasteTextSection');
  const dropZone = document.getElementById('dropZone');
  const resumeFileInput = document.getElementById('resumeFileInput');
  const browseFileBtn = document.getElementById('browseFileBtn');
  const selectedFileCard = document.getElementById('selectedFileCard');
  const selectedFileName = document.getElementById('selectedFileName');
  const selectedFileSize = document.getElementById('selectedFileSize');
  const removeFileBtn = document.getElementById('removeFileBtn');
  const resumeTextInput = document.getElementById('resumeTextInput');
  const analysisProgress = document.getElementById('analysisProgress');
  const progressStatusText = document.getElementById('progressStatusText');
  const startTargetLinkedInBtn = document.getElementById('startTargetLinkedInBtn');
  const geoNepal = document.getElementById('geoNepal');
  const geoIndia = document.getElementById('geoIndia');
  const geoWorldwide = document.getElementById('geoWorldwide');

  // Job Details Modal Elements
  const jobModal = document.getElementById('jobModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalSourceBadge = document.getElementById('modalSourceBadge');
  const modalJobTitle = document.getElementById('modalJobTitle');
  const modalJobCompany = document.getElementById('modalJobCompany');
  const modalMatchBanner = document.getElementById('modalMatchBanner');
  const modalMatchScore = document.getElementById('modalMatchScore');
  const modalMatchReasons = document.getElementById('modalMatchReasons');
  const modalJobLocation = document.getElementById('modalJobLocation');
  const modalJobSalary = document.getElementById('modalJobSalary');
  const modalJobDate = document.getElementById('modalJobDate');
  const modalJobTags = document.getElementById('modalJobTags');
  const modalJobDescription = document.getElementById('modalJobDescription');
  const modalApplyBtn = document.getElementById('modalApplyBtn');
  const modalCopyBtn = document.getElementById('modalCopyBtn');

  // Toast
  const toastNotification = document.getElementById('toastNotification');
  const toastMessage = document.getElementById('toastMessage');
  let toastTimeout = null;

  function showToast(message) {
    if (toastTimeout) clearTimeout(toastTimeout);
    toastMessage.textContent = message;
    toastNotification.classList.remove('hidden');
    toastTimeout = setTimeout(() => {
      toastNotification.classList.add('hidden');
    }, 3000);
  }

  // Debounce utility
  function debounce(fn, delay = 300) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  // ==========================================
  // Fetch / Load Jobs
  // ==========================================
  async function loadJobs(forceRefresh = false) {
    if (state.isMatchingMode) {
      applyClientFilteringAndRender();
      return;
    }

    renderLoadingSkeletons();

    try {
      const params = new URLSearchParams({
        page: state.page,
        page_size: state.pageSize,
        remote_only: 'true'
      });

      if (state.query) params.append('q', state.query);
      if (state.provider && state.provider !== 'all') params.append('provider', state.provider);
      if (state.salaryOnly) params.append('salary_only', 'true');
      if (forceRefresh) params.append('refresh', 'true');

      const response = await fetch(`/api/jobs?${params.toString()}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      state.jobs = data.jobs || [];
      state.totalJobs = data.total || 0;
      state.totalPages = data.total_pages || 1;

      if (data.stats) updateStats(data.stats);

      applySorting();
      renderJobs();
      renderPagination();
    } catch (err) {
      console.error('Failed to load jobs:', err);
      resultsCount.textContent = 'Error loading listings. Please try again.';
      jobsContainer.innerHTML = '';
      emptyState.classList.remove('hidden');
    }
  }

  function applyClientFilteringAndRender() {
    let dataset = [...state.matchedJobs];

    // Filter by provider
    if (state.provider && state.provider !== 'all') {
      dataset = dataset.filter(j => j.source.toLowerCase() === state.provider.toLowerCase());
    }

    // Filter by salary
    if (state.salaryOnly) {
      dataset = dataset.filter(j => j.has_salary);
    }

    // Filter by search query
    if (state.query) {
      const q = state.query.toLowerCase();
      dataset = dataset.filter(j => {
        const titleMatch = (j.title || '').toLowerCase().includes(q);
        const companyMatch = (j.company || '').toLowerCase().includes(q);
        const descMatch = (j.description || '').toLowerCase().includes(q);
        const tagsMatch = (j.tags || []).some(t => String(t).toLowerCase().includes(q));
        return titleMatch || companyMatch || descMatch || tagsMatch;
      });
    }

    // Sorting
    if (state.sortBy === 'match') {
      dataset.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
    } else if (state.sortBy === 'salary') {
      dataset.sort((a, b) => (b.has_salary ? 1 : 0) - (a.has_salary ? 1 : 0));
    } else if (state.sortBy === 'title') {
      dataset.sort((a, b) => a.title.localeCompare(b.title));
    } else if (state.sortBy === 'company') {
      dataset.sort((a, b) => a.company.localeCompare(b.company));
    }

    state.totalJobs = dataset.length;
    state.totalPages = Math.ceil(dataset.length / state.pageSize) || 1;

    const startIdx = (state.page - 1) * state.pageSize;
    state.jobs = dataset.slice(startIdx, startIdx + state.pageSize);

    renderJobs();
    renderPagination();
  }

  function updateStats(stats) {
    if (statTotalJobs) statTotalJobs.textContent = stats.total_jobs || '0';
    if (statSalaryCount) statSalaryCount.textContent = stats.with_salary || '0';
    if (statLastSync) statLastSync.textContent = stats.last_updated ? stats.last_updated.split(' ')[1] + ' UTC' : 'Live';
    if (statCacheAge) statCacheAge.textContent = `Age: ${stats.cache_age_seconds || 0}s (Instant cache)`;
  }

  function renderLoadingSkeletons() {
    emptyState.classList.add('hidden');
    resultsCount.textContent = 'Scanning live job feeds...';
    jobsContainer.innerHTML = `
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    `;
  }

  function applySorting() {
    if (state.sortBy === 'match') {
      state.jobs.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
    } else if (state.sortBy === 'salary') {
      state.jobs.sort((a, b) => (b.has_salary ? 1 : 0) - (a.has_salary ? 1 : 0));
    } else if (state.sortBy === 'title') {
      state.jobs.sort((a, b) => a.title.localeCompare(b.title));
    } else if (state.sortBy === 'company') {
      state.jobs.sort((a, b) => a.company.localeCompare(b.company));
    }
  }

  // ==========================================
  // Render Jobs
  // ==========================================
  function renderJobs() {
    jobsContainer.innerHTML = '';

    if (state.jobs.length === 0) {
      emptyState.classList.remove('hidden');
      paginationContainer.classList.add('hidden');
      resultsCount.textContent = '0 positions found';
      return;
    }

    emptyState.classList.add('hidden');

    if (state.isMatchingMode && state.candidateProfile) {
      resultsCount.textContent = `🎯 ${state.totalJobs} Personalized Recommendations for ${state.candidateProfile.candidate_name}`;
    } else {
      resultsCount.textContent = `${state.totalJobs} remote positions available`;
    }

    if (state.query) {
      activeQueryBadge.textContent = `Filter: "${state.query}"`;
      activeQueryBadge.classList.remove('hidden');
    } else {
      activeQueryBadge.classList.add('hidden');
    }

    state.jobs.forEach(job => {
      const card = createJobCard(job);
      jobsContainer.appendChild(card);
    });
  }

  function createJobCard(job) {
    const card = document.createElement('article');
    card.className = 'job-card';
    card.style.setProperty('--card-source-color', job.source_color || '#6366f1');

    const sourceBadgeBg = hexToRgba(job.source_color || '#6366f1', 0.14);
    const sourceBadgeBorder = hexToRgba(job.source_color || '#6366f1', 0.35);

    // Match Score Badge HTML
    let matchScoreHtml = '';
    if (job.match_score !== undefined) {
      const scoreClass = job.match_score >= 80 ? 'match-score-high' : (job.match_score >= 60 ? 'match-score-med' : 'match-score-low');
      matchScoreHtml = `
        <div class="match-score-badge ${scoreClass}">
          <span>✦</span> ${job.match_score}% Match
        </div>
      `;
    }

    // Geo Badge (e.g. 🇳🇵 Nepal Remote / 🇮🇳 India Remote / 🌍 Worldwide Remote)
    let geoBadgeHtml = '';
    if (job.geo_badge) {
      const gColor = job.geo_badge_color || '#10b981';
      geoBadgeHtml = `
        <span class="source-badge" style="background:${hexToRgba(gColor, 0.14)}; border:1px solid ${hexToRgba(gColor, 0.4)}; color:${gColor}; font-size: 0.725rem; font-weight: 700;">
          ${escapeHtml(job.geo_badge)}
        </span>
      `;
    }

    // Match Fit Box (Why you match)
    let fitBoxHtml = '';
    if (job.fit_reasons && job.fit_reasons.length > 0) {
      fitBoxHtml = `
        <div class="card-fit-box">
          <div class="fit-reason-text">
            <span class="fit-check">✓</span>
            <span>${escapeHtml(job.fit_reasons[0])}</span>
          </div>
        </div>
      `;
    }

    // Tags markup (highlight matched candidate skills)
    const candidateSkillsLower = state.candidateProfile ? new Set(state.candidateProfile.skills.map(s => s.toLowerCase())) : new Set();
    const matchedSkillsSet = new Set((job.matched_skills || []).map(s => s.toLowerCase()));
    
    const displayTags = [];
    (job.matched_skills || []).slice(0, 4).forEach(s => displayTags.push({ text: s, isMatched: true }));
    (job.tags || []).forEach(t => {
      const isM = candidateSkillsLower.has(String(t).toLowerCase()) || matchedSkillsSet.has(String(t).toLowerCase());
      if (!displayTags.some(dt => dt.text.toLowerCase() === String(t).toLowerCase()) && displayTags.length < 6) {
        displayTags.push({ text: String(t), isMatched: isM });
      }
    });

    const tagsHtml = displayTags
      .map(item => {
        const matchedClass = item.isMatched ? 'tag-item tag-item-matched' : 'tag-item';
        return `<span class="${matchedClass}">${item.isMatched ? '✓ ' : ''}${escapeHtml(item.text)}</span>`;
      })
      .join('');

    card.innerHTML = `
      <div>
        <div class="card-top">
          <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
            <div class="source-badge" style="background:${sourceBadgeBg}; border:1px solid ${sourceBadgeBorder}; color:${job.source_color}">
              <span class="source-badge-dot"></span>
              ${escapeHtml(job.source)}
            </div>
            ${geoBadgeHtml}
            ${matchScoreHtml}
          </div>
          <span class="meta-pill" style="font-size:0.75rem; color:var(--text-muted);">
            ${formatDate(job.date)}
          </span>
        </div>

        <div class="company-title-wrap">
          <div class="job-company">${escapeHtml(job.company || 'Unknown Company')}</div>
          <h3 class="job-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</h3>
        </div>

        <div class="card-meta-row" style="margin: 0.85rem 0;">
          <span class="meta-pill">
            <span>📍</span> ${escapeHtml(job.location || 'Remote')}
          </span>
          ${job.has_salary ? `
            <span class="salary-pill">
              <span>💰</span> ${escapeHtml(job.salary)}
            </span>
          ` : ''}
        </div>

        ${fitBoxHtml}

        <p class="job-excerpt">${escapeHtml(job.excerpt || '')}</p>
      </div>

      <div>
        <div class="job-tags-row" style="margin-bottom: 0.85rem;">
          ${tagsHtml}
        </div>

        <div class="card-actions-row">
          <button class="btn btn-secondary view-details-btn" data-job-id="${escapeHtml(job.id)}">
            Quick View
          </button>
          <a href="${escapeHtml(job.apply_url || '#')}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="text-decoration:none;">
            Apply ↗
          </a>
        </div>
      </div>
    `;

    // Click events
    const viewBtn = card.querySelector('.view-details-btn');
    const titleBtn = card.querySelector('.job-title');

    viewBtn.addEventListener('click', () => openJobModal(job));
    titleBtn.addEventListener('click', () => openJobModal(job));

    return card;
  }

  function openJobModal(job) {
    state.selectedJob = job;

    modalSourceBadge.textContent = job.source;
    modalSourceBadge.style.color = job.source_color;
    modalSourceBadge.style.background = hexToRgba(job.source_color, 0.15);
    modalSourceBadge.style.borderColor = hexToRgba(job.source_color, 0.4);

    modalJobTitle.textContent = job.title;
    modalJobCompany.textContent = job.company;
    modalJobLocation.textContent = job.location || 'Worldwide / Remote';
    modalJobSalary.textContent = job.salary || 'Not specified';
    modalJobDate.textContent = formatDate(job.date);

    // Match Highlight in modal
    if (job.match_score !== undefined) {
      modalMatchBanner.classList.remove('hidden');
      modalMatchScore.textContent = `${job.match_score}% Match • ${job.match_grade || 'High Alignment'}`;
      if (job.fit_reasons && job.fit_reasons.length > 0) {
        modalMatchReasons.innerHTML = job.fit_reasons
          .map(r => `<div>✔ ${escapeHtml(r)}</div>`)
          .join('');
      } else {
        modalMatchReasons.innerHTML = '';
      }
    } else {
      modalMatchBanner.classList.add('hidden');
    }

    // Tags
    modalJobTags.innerHTML = (job.tags || [])
      .map(t => `<span class="tag-item" style="font-size:0.8rem; padding:0.25rem 0.65rem;">${escapeHtml(t)}</span>`)
      .join('');

    // Description
    if (job.description) {
      modalJobDescription.innerHTML = sanitizeJobHtml(job.description);
    } else {
      modalJobDescription.textContent = job.excerpt || 'No description provided.';
    }

    modalApplyBtn.href = job.apply_url || '#';

    if (typeof jobModal.showModal === 'function') {
      jobModal.showModal();
    } else {
      jobModal.setAttribute('open', 'true');
    }
  }

  function closeJobModal() {
    if (typeof jobModal.close === 'function') {
      jobModal.close();
    } else {
      jobModal.removeAttribute('open');
    }
    state.selectedJob = null;
  }

  function renderPagination() {
    if (state.totalPages <= 1) {
      paginationContainer.classList.add('hidden');
      return;
    }

    paginationContainer.classList.remove('hidden');
    pageIndicator.textContent = `Page ${state.page} of ${state.totalPages}`;
    prevPageBtn.disabled = state.page <= 1;
    nextPageBtn.disabled = state.page >= state.totalPages;
  }

  // ==========================================
  // Resume Upload & Matching Handlers
  // ==========================================
  function openResumeModal() {
    if (typeof resumeUploadModal.showModal === 'function') {
      resumeUploadModal.showModal();
    } else {
      resumeUploadModal.setAttribute('open', 'true');
    }
  }

  function closeResumeModal() {
    if (typeof resumeUploadModal.close === 'function') {
      resumeUploadModal.close();
    } else {
      resumeUploadModal.removeAttribute('open');
    }
    analysisProgress.classList.add('hidden');
  }

  // Header & Tab triggers
  headerResumeBtn.addEventListener('click', openResumeModal);
  if (reuploadResumeBtn) reuploadResumeBtn.addEventListener('click', openResumeModal);

  tabResumeMatch.addEventListener('click', () => {
    tabBrowseJobs.classList.remove('active');
    tabResumeMatch.classList.add('active');
    if (!state.isMatchingMode || !state.candidateProfile) {
      openResumeModal();
    }
  });

  tabBrowseJobs.addEventListener('click', () => {
    tabResumeMatch.classList.remove('active');
    tabBrowseJobs.classList.add('active');
    resetResumeMode();
  });

  resumeModalCloseBtn.addEventListener('click', closeResumeModal);
  cancelResumeBtn.addEventListener('click', closeResumeModal);

  // Switch between Upload File & Paste Text
  tabUploadFile.addEventListener('click', () => {
    tabUploadFile.classList.add('active');
    tabPasteText.classList.remove('active');
    fileUploadSection.classList.remove('hidden');
    pasteTextSection.classList.add('hidden');
    updateStartButtonState();
  });

  tabPasteText.addEventListener('click', () => {
    tabPasteText.classList.add('active');
    tabUploadFile.classList.remove('active');
    pasteTextSection.classList.remove('hidden');
    fileUploadSection.classList.add('hidden');
    updateStartButtonState();
  });

  function updateStartButtonState() {
    const isFileActive = tabUploadFile.classList.contains('active');
    const hasData = isFileActive ? !!state.selectedFile : (resumeTextInput.value.trim().length > 30);
    if (startMatchBtn) startMatchBtn.disabled = !hasData;
    if (startTargetLinkedInBtn) startTargetLinkedInBtn.disabled = !hasData;
  }

  // Drag & Drop
  browseFileBtn.addEventListener('click', () => resumeFileInput.click());

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  resumeFileInput.addEventListener('change', e => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  function handleSelectedFile(file) {
    const validExts = ['pdf', 'docx', 'doc', 'txt'];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!validExts.includes(ext)) {
      showToast('Please upload a PDF, DOCX, or TXT file.');
      return;
    }

    state.selectedFile = file;
    selectedFileName.textContent = file.name;
    selectedFileSize.textContent = formatBytes(file.size);
    selectedFileCard.classList.remove('hidden');
    updateStartButtonState();
  }

  removeFileBtn.addEventListener('click', () => {
    state.selectedFile = null;
    resumeFileInput.value = '';
    selectedFileCard.classList.add('hidden');
    updateStartButtonState();
  });

  resumeTextInput.addEventListener('input', updateStartButtonState);

  // Submit Resume for Matching
  startMatchBtn.addEventListener('click', async () => {
    analysisProgress.classList.remove('hidden');
    progressStatusText.textContent = 'Parsing resume and extracting skills & experience...';
    startMatchBtn.disabled = true;

    try {
      const formData = new FormData();
      const isFile = tabUploadFile.classList.contains('active');

      if (isFile && state.selectedFile) {
        formData.append('file', state.selectedFile);
      } else {
        const text = resumeTextInput.value.trim();
        if (!text) throw new Error('Please enter resume text');
        formData.append('raw_text', text);
      }

      progressStatusText.textContent = 'Matching skills against 6 live job feeds (LinkedIn, RemoteOK, Himalayas, Arbeitnow, Jobicy, Remotive)...';

      const response = await fetch('/api/resume/match', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to match resume.');
      }

      const result = await response.json();
      state.candidateProfile = result.profile;
      state.matchedJobs = result.jobs || [];
      state.isMatchingMode = true;

      // Update UI to Match Mode
      activateCandidateRibbon(result.profile);
      closeResumeModal();
      showToast(`Matched ${result.total_matches} jobs for ${result.profile.candidate_name}!`);

      // Switch to Match sort option
      optSortMatch.classList.remove('hidden');
      sortSelect.value = 'match';
      state.sortBy = 'match';
      state.page = 1;

      tabBrowseJobs.classList.remove('active');
      tabResumeMatch.classList.add('active');

      applyClientFilteringAndRender();
    } catch (err) {
      console.error(err);
      showToast(`Error: ${err.message}`);
      analysisProgress.classList.add('hidden');
      startMatchBtn.disabled = false;
    }
  });

  // Targeted LinkedIn Matcher for Nepal & India Remote Roles
  if (startTargetLinkedInBtn) {
    startTargetLinkedInBtn.addEventListener('click', async () => {
      analysisProgress.classList.remove('hidden');
      progressStatusText.textContent = 'Extracting skills and generating specialized search queries...';
      startTargetLinkedInBtn.disabled = true;
      if (startMatchBtn) startMatchBtn.disabled = true;

      try {
        const formData = new FormData();
        const isFile = tabUploadFile.classList.contains('active');

        if (isFile && state.selectedFile) {
          formData.append('file', state.selectedFile);
        } else {
          const text = resumeTextInput.value.trim();
          if (!text) throw new Error('Please enter resume text');
          formData.append('raw_text', text);
        }

        const selectedLocs = [];
        if (geoNepal && geoNepal.checked) selectedLocs.push('Nepal');
        if (geoIndia && geoIndia.checked) selectedLocs.push('India');
        if (selectedLocs.length === 0) selectedLocs.push('Nepal', 'India');

        formData.append('locations', selectedLocs.join(','));
        formData.append('include_worldwide', geoWorldwide && geoWorldwide.checked ? 'true' : 'false');
        formData.append('time_filter', 'month');

        progressStatusText.textContent = `Scraping live LinkedIn remote jobs for ${selectedLocs.join(' & ')}...`;

        const response = await fetch('/api/resume/linkedin-target-match', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to match resume to LinkedIn.');
        }

        const result = await response.json();
        state.candidateProfile = result.profile;
        state.matchedJobs = result.jobs || [];
        state.isMatchingMode = true;

        // Update UI to Match Mode
        activateCandidateRibbon(result.profile);
        closeResumeModal();
        showToast(`🎯 Found ${result.total_matches} remote LinkedIn jobs for Nepal & India!`);

        // Switch to Match sort option
        optSortMatch.classList.remove('hidden');
        sortSelect.value = 'match';
        state.sortBy = 'match';
        state.page = 1;

        tabBrowseJobs.classList.remove('active');
        tabResumeMatch.classList.add('active');

        applyClientFilteringAndRender();
      } catch (err) {
        console.error(err);
        showToast(`Error: ${err.message}`);
      } finally {
        analysisProgress.classList.add('hidden');
        updateStartButtonState();
      }
    });
  }

  function activateCandidateRibbon(profile) {
    candidateRibbon.classList.remove('hidden');
    ribbonName.textContent = profile.candidate_name || 'Candidate';
    ribbonExpBadge.textContent = `${profile.years_of_experience}+ Years Exp • ${profile.seniority}`;
    ribbonRole.textContent = profile.primary_role;

    // Initials Avatar
    const initials = (profile.candidate_name || 'Candidate')
      .split(' ')
      .filter(w => w)
      .slice(0, 2)
      .map(w => w[0].toUpperCase())
      .join('');
    ribbonAvatar.textContent = initials || 'JD';

    // Skills cloud
    ribbonSkillsList.innerHTML = (profile.skills || [])
      .map(s => `<span class="candidate-skill-chip">${escapeHtml(s)}</span>`)
      .join('');
  }

  function resetResumeMode() {
    state.isMatchingMode = false;
    candidateRibbon.classList.add('hidden');
    optSortMatch.classList.add('hidden');
    sortSelect.value = 'default';
    state.sortBy = 'default';
    state.page = 1;
    loadJobs();
  }

  if (clearResumeBtn) {
    clearResumeBtn.addEventListener('click', () => {
      resetResumeMode();
      showToast('Switched back to all live jobs.');
    });
  }

  // ==========================================
  // General Helpers & Listeners
  // ==========================================
  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function hexToRgba(hex, alpha = 1) {
    if (!hex || !hex.startsWith('#')) return `rgba(99, 102, 241, ${alpha})`;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function sanitizeJobHtml(raw) {
    if (!raw) return '';
    return raw
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
  }

  function formatDate(d) {
    if (!d) return 'Recently';
    try {
      const date = new Date(d);
      if (isNaN(date.getTime())) return 'Recently';
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return 'Recently';
    }
  }

  // Search input with debounce
  const debouncedSearch = debounce(val => {
    state.query = val;
    state.page = 1;
    loadJobs();
  }, 300);

  searchInput.addEventListener('input', e => {
    const val = e.target.value.trim();
    clearSearchBtn.classList.toggle('hidden', val.length === 0);
    debouncedSearch(val);
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.classList.add('hidden');
    state.query = '';
    state.page = 1;
    loadJobs();
    searchInput.focus();
  });

  // Keyboard shortcut: '/' to focus search, 'Escape' to close modal
  window.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== searchInput && document.activeElement !== resumeTextInput) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    } else if (e.key === 'Escape') {
      if (jobModal && jobModal.open) closeJobModal();
      if (resumeUploadModal && resumeUploadModal.open) closeResumeModal();
    }
  });

  // Provider Filter Chips
  providerChips.forEach(chip => {
    chip.addEventListener('click', () => {
      providerChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.provider = chip.dataset.provider;
      state.page = 1;
      loadJobs();
    });
  });

  // Salary Toggle
  salaryToggle.addEventListener('change', e => {
    state.salaryOnly = e.target.checked;
    state.page = 1;
    loadJobs();
  });

  // Sorting
  sortSelect.addEventListener('change', e => {
    state.sortBy = e.target.value;
    if (state.isMatchingMode) {
      applyClientFilteringAndRender();
    } else {
      applySorting();
      renderJobs();
    }
  });

  // Refresh Feeds Button
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      if (spinIcon) spinIcon.classList.add('spinning');
      refreshBtn.disabled = true;
      showToast('Syncing all 5 live job feeds...');
      await loadJobs(true);
      if (spinIcon) spinIcon.classList.remove('spinning');
      refreshBtn.disabled = false;
      showToast('Feeds successfully updated!');
    });
  }

  // Reset Filters
  resetFiltersBtn.addEventListener('click', () => {
    state.query = '';
    state.provider = 'all';
    state.salaryOnly = false;
    state.page = 1;
    searchInput.value = '';
    clearSearchBtn.classList.add('hidden');
    salaryToggle.checked = false;
    providerChips.forEach(c => c.classList.toggle('active', c.dataset.provider === 'all'));
    loadJobs();
  });

  // Pagination
  prevPageBtn.addEventListener('click', () => {
    if (state.page > 1) {
      state.page--;
      loadJobs();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });

  nextPageBtn.addEventListener('click', () => {
    if (state.page < state.totalPages) {
      state.page++;
      loadJobs();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });

  // Modal Backdrop Close Listeners
  modalCloseBtn.addEventListener('click', closeJobModal);
  jobModal.addEventListener('click', e => {
    const rect = jobModal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width
    );
    if (!isInDialog) closeJobModal();
  });

  resumeUploadModal.addEventListener('click', e => {
    const rect = resumeUploadModal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width
    );
    if (!isInDialog) closeResumeModal();
  });

  modalCopyBtn.addEventListener('click', () => {
    if (state.selectedJob && state.selectedJob.apply_url) {
      navigator.clipboard.writeText(state.selectedJob.apply_url).then(() => {
        showToast('Application link copied to clipboard!');
      });
    }
  });

  // Initial load
  loadJobs();
});
