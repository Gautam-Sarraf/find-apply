/**
 * findit. - Client Application Logic with Glass & Gradient UI
 * Supports Foundit-style Hero & Floating Search + Talentium-style Dashboard & Job Cards
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    query: '',
    provider: 'all',
    geoRegion: 'all',
    salaryOnly: false,
    sortBy: 'default',
    page: 1,
    pageSize: 24,
    totalJobs: 0,
    totalPages: 1,
    jobs: [],
    selectedJob: null,
    bookmarkedIds: new Set(JSON.parse(localStorage.getItem('findit_bookmarks') || '[]')),

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
  const cardSearchBtn = document.getElementById('cardSearchBtn');
  const locationFilterInput = document.getElementById('locationFilterInput');
  const providerChips = document.querySelectorAll('#providerFilterGroup .chip');
  const geoChips = document.querySelectorAll('.geo-chip');
  const salaryToggle = document.getElementById('salaryToggle');
  const sortSelect = document.getElementById('sortSelect');
  const optSortMatch = document.getElementById('optSortMatch');
  const optSortDefault = document.getElementById('optSortDefault');
  const jobsContainer = document.getElementById('jobsContainer');
  const resultsCount = document.getElementById('resultsCount');
  const activeQueryBadge = document.getElementById('activeQueryBadge');
  const emptyState = document.getElementById('emptyState');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');
  const sidebarResetBtn = document.getElementById('sidebarResetBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const spinIcon = refreshBtn ? refreshBtn.querySelector('.spin-icon') : null;

  // Hero Actions
  const heroUploadResumeBtn = document.getElementById('heroUploadResumeBtn');
  const heroTargetGeoBtn = document.getElementById('heroTargetGeoBtn');
  const quickTags = document.querySelectorAll('.quick-tag');
  const navLinkResume = document.getElementById('navLinkResume');
  const navLinkRegions = document.getElementById('navLinkRegions');

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
  const startTargetLinkedInBtn = document.getElementById('startTargetLinkedInBtn');
  const geoNepal = document.getElementById('geoNepal');
  const geoIndia = document.getElementById('geoIndia');
  const geoUS = document.getElementById('geoUS');
  const geoUK = document.getElementById('geoUK');
  const geoWorldwide = document.getElementById('geoWorldwide');
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
    }, 3200);
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
      let rawJobs = data.jobs || [];

      // Filter by Geo Region if selected in sidebar
      if (state.geoRegion && state.geoRegion !== 'all') {
        const g = state.geoRegion.toLowerCase();
        rawJobs = rawJobs.filter(j => {
          const loc = (j.location || '').toLowerCase();
          const desc = (j.description || '').toLowerCase();
          const badge = (j.geo_badge || '').toLowerCase();
          const status = (j.geo_status || '').toLowerCase();
          if (g === 'us') {
            return loc.includes('united states') || loc.includes('us') || badge.includes('us') || status.includes('us');
          }
          if (g === 'uk') {
            return loc.includes('united kingdom') || loc.includes('uk') || loc.includes('london') || badge.includes('uk') || status.includes('uk');
          }
          return loc.includes(g) || desc.includes(g) || badge.includes(g);
        });
      }

      state.jobs = rawJobs;
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
      dataset = dataset.filter(j => (j.source || '').toLowerCase() === state.provider.toLowerCase());
    }

    // Filter by salary
    if (state.salaryOnly) {
      dataset = dataset.filter(j => j.has_salary);
    }

    // Filter by Geo Region
    if (state.geoRegion && state.geoRegion !== 'all') {
      const g = state.geoRegion.toLowerCase();
      dataset = dataset.filter(j => {
        const loc = (j.location || '').toLowerCase();
        const desc = (j.description || '').toLowerCase();
        const badge = (j.geo_badge || '').toLowerCase();
        const status = (j.geo_status || '').toLowerCase();
        if (g === 'us') {
          return loc.includes('united states') || loc.includes('us') || badge.includes('us') || status.includes('us');
        }
        if (g === 'uk') {
          return loc.includes('united kingdom') || loc.includes('uk') || loc.includes('london') || badge.includes('uk') || status.includes('uk');
        }
        return loc.includes(g) || desc.includes(g) || badge.includes(g);
      });
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
      dataset.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (state.sortBy === 'company') {
      dataset.sort((a, b) => (a.company || '').localeCompare(b.company || ''));
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
      state.jobs.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (state.sortBy === 'company') {
      state.jobs.sort((a, b) => (a.company || '').localeCompare(b.company || ''));
    }
  }

  // ==========================================
  // Render Jobs (Talentium Style Grid)
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
      resultsCount.textContent = `${state.totalJobs} recommendations for ${state.candidateProfile.candidate_name}`;
    } else {
      resultsCount.textContent = `Showing ${state.jobs.length} of ${state.totalJobs} remote positions`;
    }

    if (state.query) {
      activeQueryBadge.textContent = `Filter: "${state.query}"`;
      activeQueryBadge.classList.remove('hidden');
    } else {
      activeQueryBadge.classList.add('hidden');
    }

    state.jobs.forEach((job, index) => {
      // After index 2, insert the Talentium-style promo gradient banner card
      if (index === 2 && !state.isMatchingMode) {
        const promoCard = createPromoCard();
        jobsContainer.appendChild(promoCard);
      }
      const card = createJobCard(job);
      jobsContainer.appendChild(card);
    });
  }

  function createPromoCard() {
    const card = document.createElement('article');
    card.className = 'promo-talentium-card';
    card.innerHTML = `
      <div>
        <span class="promo-talentium-tag">Find your dream job</span>
        <h3 class="promo-talentium-title">Get hired faster with AI Resume Match!</h3>
        <p class="promo-talentium-desc">Upload your resume to automatically rank jobs with 90%+ skill match and Nepal/India remote eligibility.</p>
      </div>
      <div>
        <button type="button" class="btn-promo-action" id="promoCardUploadBtn">
          Match My Resume
        </button>
      </div>
    `;
    const btn = card.querySelector('#promoCardUploadBtn');
    if (btn) btn.addEventListener('click', openResumeModal);
    return card;
  }

  // ==========================================
  // Talentium Job Card Creation
  // ==========================================
  function createJobCard(job) {
    const card = document.createElement('article');
    card.className = 'job-card';

    // Source pill styling
    const sourceBadgeBg = hexToRgba(job.source_color || '#6366f1', 0.12);
    const sourceBadgeBorder = hexToRgba(job.source_color || '#6366f1', 0.35);

    // Salary Display (Talentium top-left prominence)
    let salaryHtml = '';
    if (job.has_salary && job.salary && job.salary !== 'Not specified') {
      salaryHtml = `<div class="card-salary-badge text-emerald">${escapeHtml(job.salary)}</div>`;
    } else {
      salaryHtml = `<div class="card-salary-badge salary-empty">Competitive</div>`;
    }

    // Company Logo / Avatar
    let logoHtml = '';
    const companyName = job.company || 'Company';
    if (job.company_logo && job.company_logo.startsWith('http')) {
      logoHtml = `
        <div class="company-logo-avatar">
          <img src="${escapeHtml(job.company_logo)}" class="company-logo-img" alt="${escapeHtml(companyName)}" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'company-logo-initials\\'>${getInitials(companyName)}</span>'">
        </div>
      `;
    } else {
      logoHtml = `
        <div class="company-logo-avatar">
          <span class="company-logo-initials">${getInitials(companyName)}</span>
        </div>
      `;
    }

    // Match Score Badge HTML
    let matchScoreHtml = '';
    if (job.match_score !== undefined) {
      const scoreClass = job.match_score >= 80 ? 'match-score-high' : (job.match_score >= 60 ? 'match-score-med' : 'match-score-low');
      matchScoreHtml = `
        <div class="match-score-badge ${scoreClass}">
          ${job.match_score}% Match
        </div>
      `;
    }

    // Geo Badge
    let geoBadgeHtml = '';
    if (job.geo_badge) {
      const gColor = job.geo_badge_color || '#10b981';
      geoBadgeHtml = `
        <span class="geo-badge-tag" style="background:${hexToRgba(gColor, 0.12)}; border:1px solid ${hexToRgba(gColor, 0.35)}; color:${gColor};">
          ${escapeHtml(job.geo_badge)}
        </span>
      `;
    }

    // Fit Reason Box (when matched)
    let fitBoxHtml = '';
    if (job.fit_reasons && job.fit_reasons.length > 0) {
      fitBoxHtml = `
        <div class="card-fit-box">
          <span>${escapeHtml(job.fit_reasons[0])}</span>
        </div>
      `;
    }

    // Tags row with matched candidate skills prioritization
    const candidateSkillsLower = state.candidateProfile ? new Set(state.candidateProfile.skills.map(s => s.toLowerCase())) : new Set();
    const matchedSkillsSet = new Set((job.matched_skills || []).map(s => s.toLowerCase()));
    
    const displayTags = [];
    (job.matched_skills || []).slice(0, 4).forEach(s => displayTags.push({ text: s, isMatched: true }));
    (job.tags || []).forEach(t => {
      const isM = candidateSkillsLower.has(String(t).toLowerCase()) || matchedSkillsSet.has(String(t).toLowerCase());
      if (!displayTags.some(dt => dt.text.toLowerCase() === String(t).toLowerCase()) && displayTags.length < 5) {
        displayTags.push({ text: String(t), isMatched: isM });
      }
    });

    const tagsHtml = displayTags
      .map(item => {
        const matchedClass = item.isMatched ? 'tag-item tag-item-matched' : 'tag-item';
        return `<span class="${matchedClass}">${escapeHtml(item.text)}</span>`;
      })
      .join('');

    const isBookmarked = state.bookmarkedIds.has(job.id);

    card.innerHTML = `
      <div>
        <!-- Talentium Top Row: Salary on Left, Logo + Source on Right -->
        <div class="card-talentium-top">
          ${salaryHtml}
          <div class="card-company-logo-wrap">
            <div class="source-badge" style="background:${sourceBadgeBg}; border:1px solid ${sourceBadgeBorder}; color:${job.source_color}">
              <span class="source-badge-dot"></span>
              ${escapeHtml(job.source)}
            </div>
            ${logoHtml}
          </div>
        </div>

        <!-- Role Title & Company Subtitle -->
        <div class="card-talentium-body">
          <h3 class="job-role-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</h3>
          <div class="job-company-subtitle">
            <span>${escapeHtml(companyName)}</span>
            <span class="company-dot-separator">•</span>
            <span>${escapeHtml(job.location || 'Remote')}</span>
            <span class="company-dot-separator">•</span>
            <span>${formatDate(job.date)}</span>
          </div>

          <!-- Badges: Regional Geo & Match Score -->
          <div class="card-badges-row">
            ${geoBadgeHtml}
            ${matchScoreHtml}
          </div>

          ${fitBoxHtml}

          <p class="job-excerpt-text">${escapeHtml(job.excerpt || '')}</p>
        </div>
      </div>

      <div>
        <!-- Tags Row -->
        <div class="card-tags-row">
          ${tagsHtml}
        </div>

        <!-- Talentium Action Row: Solid Black Pill "Apply now" + Quick View + Heart -->
        <div class="card-talentium-actions">
          <a href="${escapeHtml(job.apply_url || '#')}" target="_blank" rel="noopener noreferrer" class="btn-talentium-apply">
            Apply now
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-left:4px; display:inline-block; vertical-align:-1px;">
              <path d="M7 17l9.2-9.2M17 17V8H8"/>
            </svg>
          </a>
          <button type="button" class="btn-quick-view view-details-btn" data-job-id="${escapeHtml(job.id)}">
            Quick View
          </button>
          <button type="button" class="btn-bookmark ${isBookmarked ? 'bookmarked' : ''}" aria-label="Bookmark job" title="Save job">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="${isBookmarked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
            </svg>
          </button>
        </div>
      </div>
    `;

    // Click events
    const viewBtn = card.querySelector('.view-details-btn');
    const titleBtn = card.querySelector('.job-role-title');
    const bookmarkBtn = card.querySelector('.btn-bookmark');

    viewBtn.addEventListener('click', () => openJobModal(job));
    titleBtn.addEventListener('click', () => openJobModal(job));

    bookmarkBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.bookmarkedIds.has(job.id)) {
        state.bookmarkedIds.delete(job.id);
        bookmarkBtn.classList.remove('bookmarked');
        bookmarkBtn.querySelector('svg').setAttribute('fill', 'none');
        showToast('Job removed from saved list');
      } else {
        state.bookmarkedIds.add(job.id);
        bookmarkBtn.classList.add('bookmarked');
        bookmarkBtn.querySelector('svg').setAttribute('fill', 'currentColor');
        showToast('Job saved to bookmarks');
      }
      localStorage.setItem('findit_bookmarks', JSON.stringify([...state.bookmarkedIds]));
    });

    return card;
  }

  function getInitials(name) {
    if (!name) return 'CO';
    const words = name.trim().split(/\s+/);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
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
      modalMatchScore.textContent = `${job.match_score}% Match • High Alignment`;
      if (job.fit_reasons && job.fit_reasons.length > 0) {
        modalMatchReasons.innerHTML = job.fit_reasons
          .map(r => `<div>${escapeHtml(r)}</div>`)
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
    if (job.description && job.description.length > 50) {
      modalJobDescription.innerHTML = sanitizeHtml(job.description);
    } else {
      modalJobDescription.textContent = job.excerpt || 'No additional description provided. Click Apply to view full listing.';
    }

    modalApplyBtn.href = job.apply_url || '#';

    jobModal.showModal();
    document.body.style.overflow = 'hidden';
  }

  function closeJobModal() {
    jobModal.close();
    document.body.style.overflow = '';
  }

  function openResumeModal() {
    resumeUploadModal.showModal();
    document.body.style.overflow = 'hidden';
    updateStartButtonState();
  }

  function closeResumeModal() {
    resumeUploadModal.close();
    document.body.style.overflow = '';
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

  // Utilities
  function hexToRgba(hex, alpha = 1) {
    if (!hex || !hex.startsWith('#')) return `rgba(99, 102, 241, ${alpha})`;
    let c = hex.substring(1);
    if (c.length === 3) c = c.split('').map(x => x + x).join('');
    const num = parseInt(c, 16);
    return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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

  function sanitizeHtml(raw) {
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

  // ==========================================
  // Event Listeners
  // ==========================================
  
  // Header & Tab triggers
  if (headerResumeBtn) headerResumeBtn.addEventListener('click', openResumeModal);
  if (heroUploadResumeBtn) heroUploadResumeBtn.addEventListener('click', openResumeModal);
  if (reuploadResumeBtn) reuploadResumeBtn.addEventListener('click', openResumeModal);
  if (navLinkResume) navLinkResume.addEventListener('click', (e) => {
    e.preventDefault();
    openResumeModal();
  });

  // Hero Target Geo button
  if (heroTargetGeoBtn) {
    heroTargetGeoBtn.addEventListener('click', () => {
      state.geoRegion = 'Nepal';
      geoChips.forEach(c => c.classList.toggle('active', c.dataset.geo === 'Nepal'));
      const section = document.getElementById('exploreJobsSection');
      if (section) section.scrollIntoView({ behavior: 'smooth' });
      loadJobs();
    });
  }

  if (navLinkRegions) {
    navLinkRegions.addEventListener('click', (e) => {
      e.preventDefault();
      state.geoRegion = 'Nepal';
      geoChips.forEach(c => c.classList.toggle('active', c.dataset.geo === 'Nepal'));
      const section = document.getElementById('exploreJobsSection');
      if (section) section.scrollIntoView({ behavior: 'smooth' });
      loadJobs();
    });
  }

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

  // Drag & Drop & File Picker Guards (Keep modal firmly open during upload)
  let isSelectingFile = false;

  browseFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isSelectingFile = true;
    resumeFileInput.click();
  });

  dropZone.addEventListener('click', (e) => {
    if (e.target !== resumeFileInput) {
      e.stopPropagation();
      isSelectingFile = true;
      resumeFileInput.click();
    }
  });

  resumeFileInput.addEventListener('click', (e) => {
    e.stopPropagation();
    isSelectingFile = true;
  });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  resumeFileInput.addEventListener('change', e => {
    setTimeout(() => { isSelectingFile = false; }, 400);
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  window.addEventListener('focus', () => {
    setTimeout(() => { isSelectingFile = false; }, 400);
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

    // Ensure the modal remains open and visible
    if (!resumeUploadModal.open) {
      resumeUploadModal.showModal();
    }
  }

  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    state.selectedFile = null;
    resumeFileInput.value = '';
    selectedFileCard.classList.add('hidden');
    updateStartButtonState();
  });

  resumeTextInput.addEventListener('input', updateStartButtonState);

  // Standard Match (All Sources)
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
    } finally {
      analysisProgress.classList.add('hidden');
      updateStartButtonState();
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
        const channelsSummary = [];
        if (geoNepal && geoNepal.checked) { selectedLocs.push('Nepal'); channelsSummary.push('Nepal'); }
        if (geoIndia && geoIndia.checked) { selectedLocs.push('India'); channelsSummary.push('India'); }
        if (geoUS && geoUS.checked) { selectedLocs.push('United States'); channelsSummary.push('US Startups'); }
        if (geoUK && geoUK.checked) { selectedLocs.push('United Kingdom'); channelsSummary.push('UK Startups'); }
        if (selectedLocs.length === 0) selectedLocs.push('Nepal', 'India', 'United States', 'United Kingdom');

        formData.append('locations', selectedLocs.join(','));
        formData.append('include_worldwide', geoWorldwide && geoWorldwide.checked ? 'true' : 'false');
        formData.append('include_us_startups', geoUS && geoUS.checked ? 'true' : 'false');
        formData.append('include_uk_startups', geoUK && geoUK.checked ? 'true' : 'false');
        formData.append('time_filter', 'month');

        progressStatusText.textContent = `Scraping live LinkedIn remote jobs for ${channelsSummary.join(', ')}...`;

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
        showToast(`Found ${result.total_matches} remote jobs across Nepal, India & US/UK Startups!`);

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

  clearResumeBtn.addEventListener('click', resetResumeMode);

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

  if (cardSearchBtn) {
    cardSearchBtn.addEventListener('click', () => {
      const val = searchInput.value.trim();
      state.query = val;
      state.page = 1;
      const section = document.getElementById('exploreJobsSection');
      if (section) section.scrollIntoView({ behavior: 'smooth' });
      loadJobs();
    });
  }

  // Popular quick tags click handler
  quickTags.forEach(tag => {
    tag.addEventListener('click', () => {
      const q = tag.dataset.query;
      searchInput.value = q;
      clearSearchBtn.classList.remove('hidden');
      state.query = q;
      state.page = 1;
      const section = document.getElementById('exploreJobsSection');
      if (section) section.scrollIntoView({ behavior: 'smooth' });
      loadJobs();
    });
  });

  // Geo Chips (Sidebar)
  geoChips.forEach(chip => {
    chip.addEventListener('click', () => {
      geoChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.geoRegion = chip.dataset.geo;
      state.page = 1;
      loadJobs();
    });
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
      showToast('Syncing jobs...');
      await loadJobs(true);
      if (spinIcon) spinIcon.classList.remove('spinning');
      refreshBtn.disabled = false;
      showToast('Jobs updated');
    });
  }

  // Reset Filters (Main & Sidebar)
  function resetAllFilters() {
    state.query = '';
    state.provider = 'all';
    state.geoRegion = 'all';
    state.salaryOnly = false;
    state.page = 1;
    searchInput.value = '';
    clearSearchBtn.classList.add('hidden');
    salaryToggle.checked = false;
    providerChips.forEach(c => c.classList.toggle('active', c.dataset.provider === 'all'));
    geoChips.forEach(c => c.classList.toggle('active', c.dataset.geo === 'all'));
    loadJobs();
    showToast('Filters reset to default');
  }

  if (resetFiltersBtn) resetFiltersBtn.addEventListener('click', resetAllFilters);
  if (sidebarResetBtn) sidebarResetBtn.addEventListener('click', resetAllFilters);

  // Pagination
  prevPageBtn.addEventListener('click', () => {
    if (state.page > 1) {
      state.page--;
      loadJobs();
      window.scrollTo({ top: 400, behavior: 'smooth' });
    }
  });

  nextPageBtn.addEventListener('click', () => {
    if (state.page < state.totalPages) {
      state.page++;
      loadJobs();
      window.scrollTo({ top: 400, behavior: 'smooth' });
    }
  });

  // Modal Backdrop Close Listeners
  modalCloseBtn.addEventListener('click', closeJobModal);
  // Dialog backdrop click handling
  jobModal.addEventListener('click', e => {
    if (e.target === jobModal) closeJobModal();
  });

  const uploadModalCard = resumeUploadModal.querySelector('.modal-card');
  if (uploadModalCard) {
    uploadModalCard.addEventListener('click', e => {
      e.stopPropagation();
    });
  }

  resumeUploadModal.addEventListener('click', e => {
    if (isSelectingFile) return;
    if (e.target === resumeUploadModal) closeResumeModal();
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
