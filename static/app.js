/**
 * KAI Student OS - Core Frontend Application
 * Apple-Inspired Liquid Glass Experience for Group 5108 (2nd Subgroup)
 */

const API_BASE = '';
const AUTH_TOKEN_KEY = 'kai_app_auth_token';

function getAuthToken() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) return token;
  const match = document.cookie.match(/(?:^|;\s*)kai_app_auth_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function setAuthToken(token) {
  if (token) {
    const clean = token.trim();
    localStorage.setItem(AUTH_TOKEN_KEY, clean);
    document.cookie = `kai_app_auth_token=${encodeURIComponent(clean)}; path=/; SameSite=Strict; max-age=31536000`;
  }
}

function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  document.cookie = 'kai_app_auth_token=; path=/; max-age=0; SameSite=Strict';
}

async function apiFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
    headers.set('X-App-Token', token);
  }

  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    clearAuthToken();
    showAuthModal(true);
    throw new Error('Неавторизованный доступ');
  }
  return response;
}

async function downloadTaskFile(taskId, attachmentId = null, fallbackName = 'file') {
  try {
    let url = `${API_BASE}/api/tasks/${taskId}/download`;
    if (attachmentId !== null && attachmentId !== undefined) {
      url += `?attachment_id=${encodeURIComponent(attachmentId)}`;
    }
    const res = await apiFetch(url);
    if (!res.ok) {
      let errMsg = `Ошибка скачивания (HTTP ${res.status})`;
      try {
        const data = await res.json();
        if (data && data.detail) errMsg = data.detail;
      } catch (_) {}
      throw new Error(errMsg);
    }
    const blob = await res.blob();
    let filename = fallbackName;
    const cd = res.headers.get('content-disposition');
    if (cd) {
      const mUtf = cd.match(/filename\*=UTF-8''([^;]+)/i);
      if (mUtf) {
        filename = decodeURIComponent(mUtf[1]);
      } else {
        const m = cd.match(/filename="?([^";]+)"?/i);
        if (m) filename = m[1].trim();
      }
    }
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 15000);
  } catch (err) {
    console.error('Download failed:', err);
    if (typeof showToast === 'function') {
      showToast(err.message || 'Не удалось скачать файл', 'error');
    } else {
      alert(err.message || 'Не удалось скачать файл');
    }
  }
}
window.downloadTaskFile = downloadTaskFile;

const state = {
  currentTab: 'focus',          // 'focus' | 'tasks' | 'ai' | 'more'
  currentSegment: 'submissions', // 'submissions' | 'materials'
  scheduleDay: getInitialWeekday(), // 1..6
  scheduleParity: 'чет',        // 'чет' | 'нечет'
  tasksStatusFilter: 'all',     // 'all' | 'todo' | 'done'
  tasksSubjectFilter: 0,        // 0 = all
  searchQuery: '',
  subjects: [],
  tasks: [],
  stats: null,
  todaySchedule: [],
  isSyncing: false
};

const RUSSIAN_WEEKDAYS = {
  1: 'Понедельник',
  2: 'Вторник',
  3: 'Среда',
  4: 'Четверг',
  5: 'Пятница',
  6: 'Суббота',
  7: 'Воскресенье'
};

const BELL_SCHEDULE = [
  { slot: 1, start: '08:00', end: '09:30', startMin: 480, endMin: 570 },
  { slot: 2, start: '09:40', end: '11:10', startMin: 580, endMin: 670 },
  { slot: 3, start: '11:20', end: '12:50', startMin: 680, endMin: 770 },
  { slot: 4, start: '13:30', end: '15:00', startMin: 810, endMin: 900 },
  { slot: 5, start: '15:10', end: '16:40', startMin: 910, endMin: 1000 },
  { slot: 6, start: '16:50', end: '18:20', startMin: 1010, endMin: 1100 },
  { slot: 7, start: '18:30', end: '20:00', startMin: 1110, endMin: 1200 }
];

function getInitialWeekday() {
  const day = new Date().getDay();
  if (day === 0) return 1;
  return day;
}

// -------------------------------------------------------------
// PWA & Service Worker
// -------------------------------------------------------------
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((r) => r.update()).catch(console.warn);
  });
}

// -------------------------------------------------------------
// PIN / Passcode Authentication Modal
// -------------------------------------------------------------
function showAuthModal(isExpired = false) {
  const overlay = document.getElementById('auth-overlay');
  const errorMsg = document.getElementById('auth-error-msg');
  const tokenInput = document.getElementById('auth-token-input');
  if (!overlay) return;

  if (errorMsg) {
    if (isExpired) {
      errorMsg.textContent = 'Ключ доступа устарел или неверен. Введите ключ снова.';
      errorMsg.style.display = 'block';
    } else {
      errorMsg.style.display = 'none';
      errorMsg.textContent = '';
    }
  }
  if (tokenInput) {
    tokenInput.value = '';
    setTimeout(() => tokenInput.focus(), 150);
  }
  overlay.style.display = 'flex';
}

function hideAuthModal() {
  const overlay = document.getElementById('auth-overlay');
  if (overlay) overlay.style.display = 'none';
}

function setupAuthModalEvents() {
  const form = document.getElementById('auth-form');
  const tokenInput = document.getElementById('auth-token-input');
  const errorMsg = document.getElementById('auth-error-msg');
  const toggleBtn = document.getElementById('auth-toggle-visibility-btn');
  const submitBtn = document.getElementById('auth-submit-btn');

  if (toggleBtn && tokenInput) {
    toggleBtn.addEventListener('click', () => {
      const isPwd = tokenInput.type === 'password';
      tokenInput.type = isPwd ? 'text' : 'password';
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const val = tokenInput ? tokenInput.value.trim() : '';
      if (!val) {
        if (errorMsg) {
          errorMsg.textContent = 'Пожалуйста, введите ключ доступа';
          errorMsg.style.display = 'block';
        }
        return;
      }

      if (submitBtn) submitBtn.disabled = true;
      if (errorMsg) errorMsg.style.display = 'none';

      try {
        const res = await fetch('/api/stats', {
          headers: {
            'Authorization': `Bearer ${val}`,
            'X-App-Token': val
          }
        });

        if (res.status === 401) {
          if (errorMsg) {
            errorMsg.textContent = 'Неверный ключ доступа. Попробуйте еще раз.';
            errorMsg.style.display = 'block';
          }
          return;
        }

        if (!res.ok) {
          throw new Error('Ошибка сервера: ' + res.status);
        }

        setAuthToken(val);
        hideAuthModal();
        showToast('Успешный вход в систему');
        await initAppData();

      } catch (err) {
        console.error('Auth verification error:', err);
        if (errorMsg) {
          errorMsg.textContent = 'Ошибка проверки: ' + err.message;
          errorMsg.style.display = 'block';
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // Reset PIN button from Settings
  const resetBtn = document.getElementById('settings-reset-token-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      clearAuthToken();
      showAuthModal(false);
      showToast('Ключ сброшен');
    });
  }
}

// -------------------------------------------------------------
// App Initialization
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupThemeToggle();
  setupNavigation();
  setupSegmentControl();
  setupScheduleEvents();
  setupTasksEvents();
  setupTopBarEvents();
  setupSyncEvents();
  setupGeminiEvents();
  setupHomeComposerEvents();
  setupAuthModalEvents();
  setupTaskDetailSheet();
  setupKeyboardAvoidance();

  const token = getAuthToken();
  if (!token) {
    showAuthModal(false);
  } else {
    initAppData();
  }

  setInterval(updateLiveLessonStatus, 30000);
  setInterval(updateFreshnessDisplay, 60000);
});

async function initAppData() {
  updateCurrentDateDisplay();
  try {
    await Promise.all([
      loadTasksData(),
      loadScheduleData(),
      loadTodayScheduleForLive(),
      loadStatsData()
    ]);
    renderFocusView();
  } catch (err) {
    console.warn('initAppData interrupted (likely 401):', err);
  }
}

// -------------------------------------------------------------
// Utility & Helpers
// -------------------------------------------------------------
let toastTimeout = null;
function showToast(message, duration = 2400) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), duration);
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

function formatTeacherName(str) {
  if (!str || typeof str !== 'string') return '';
  const trimmed = str.trim();
  if (!trimmed) return '';
  return trimmed
    .toLowerCase()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function parseMinutes(timeStr) {
  if (!timeStr) return 0;
  const parts = timeStr.trim().split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1] || 0, 10);
}

function getLessonTimeRange(lesson) {
  const timeStr = (lesson.day_time || '').trim();
  if (timeStr.includes('-')) {
    const parts = timeStr.split('-');
    const s = parts[0].trim();
    const e = parts[1].trim();
    return {
      startStr: s,
      endStr: e,
      startMin: parseMinutes(s),
      endMin: parseMinutes(e),
      formatted: s + ' — ' + e
    };
  }
  const match = BELL_SCHEDULE.find((slot) => slot.start === timeStr);
  if (match) {
    return {
      startStr: match.start,
      endStr: match.end,
      startMin: match.startMin,
      endMin: match.endMin,
      formatted: match.start + ' — ' + match.end
    };
  }
  const sMin = parseMinutes(timeStr);
  const eMin = sMin + 90;
  const eHours = Math.floor(eMin / 60).toString().padStart(2, '0');
  const eMins = (eMin % 60).toString().padStart(2, '0');
  return {
    startStr: timeStr,
    endStr: eHours + ':' + eMins,
    startMin: sMin,
    endMin: eMin,
    formatted: timeStr + ' — ' + eHours + ':' + eMins
  };
}

function getBuildingBadge(buildNum, audNum) {
  const b = String(buildNum || '').toLowerCase().trim();
  const aud = audNum ? 'ауд. ' + audNum : '';
  let cls = 'bldg-2';
  let label = '';

  if (b.includes('2')) {
    cls = 'bldg-2';
    label = aud ? '2 зд. • ' + aud : '2 здание';
  } else if (b.includes('5')) {
    cls = 'bldg-5';
    label = aud ? '5 зд. • ' + aud : '5 здание';
  } else if (b.includes('7')) {
    cls = 'bldg-7';
    label = aud ? '7 зд. • ' + aud : '7 здание';
  } else if (b.includes('олимп') || b.includes('кск') || b.includes('спорт')) {
    cls = 'bldg-olimp';
    label = 'КСК Олимп';
  } else if (buildNum) {
    cls = 'bldg-2';
    label = aud ? buildNum + ' зд. • ' + aud : buildNum + ' зд.';
  } else {
    cls = 'bldg-2';
    label = aud || 'КАИ';
  }
  return { cls: cls, label: label };
}

function isReferenceMaterial(task) {
  const title = (task.title || '').toLowerCase();
  const refKeywords = [
    'программ', 'лекци', 'фос', 'методическ', 'указани', 'руководств',
    'инструкци', 'бланк', 'литератур', 'конспект', 'справочник', 'введение',
    'история', 'вопросы к', 'титульн', 'список', 'план', 'учебник', 'пособие',
    'силлабус', 'критери', 'тема ', 'презентац', 'материал', 'слайд'
  ];
  const actionKeywords = [
    'лабораторн', 'практическ', 'задани', 'отчет', 'контрольн', 'зачет',
    'аттестац', 'проверочн', 'тестирован', 'тест', 'доклад', 'семестров',
    'курсов', 'ргр', 'дз', 'экзамен', 'коллоквиум', 'расчет'
  ];
  const hasRef = refKeywords.some((kw) => title.includes(kw));
  const hasAct = actionKeywords.some((kw) => title.includes(kw));

  if (hasRef && !hasAct) return true;
  if (hasAct && !hasRef) return false;
  if (title.includes('методическ') || title.includes('программ')) return true;
  if (hasAct) return false;
  return hasRef;
}

function formatDeadlineDisplay(deadlineStr) {
  if (!deadlineStr) return '';
  try {
    const d = new Date(deadlineStr);
    if (!isNaN(d.getTime())) {
      const now = new Date();
      const diffMs = d.getTime() - now.getTime();
      const diffHours = Math.round(diffMs / (1000 * 60 * 60));
      const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

      const datePart = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
      const timePart = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

      if (diffHours > 0 && diffHours <= 24) {
        return `до ${datePart}, ${timePart} (осталось ${diffHours} ч)`;
      } else if (diffHours > 24 && diffDays <= 7) {
        return `до ${datePart}, ${timePart} (${diffDays} дн)`;
      } else if (diffHours <= 0) {
        return `срок истек (${datePart})`;
      }
      return `до ${datePart}, ${timePart}`;
    }
  } catch (e) {}
  return deadlineStr;
}

// -------------------------------------------------------------
// Top Bar & Navigation (4 Tabs: focus | tasks | ai | more)
// -------------------------------------------------------------
function getFreshnessInfo() {
  const syncIso = state.stats && state.stats.last_successful_sync;
  if (!syncIso) {
    return {
      status: 'unknown',
      text: 'Время синхронизации неизвестно',
      className: 'freshness-unknown'
    };
  }

  const syncTime = new Date(syncIso).getTime();
  if (isNaN(syncTime)) {
    return {
      status: 'unknown',
      text: 'Время синхронизации неизвестно',
      className: 'freshness-unknown'
    };
  }

  const diffMs = Date.now() - syncTime;
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000));
  const freshThreshold = (state.stats.sync_freshness_thresholds && state.stats.sync_freshness_thresholds.fresh_minutes) || 15;
  const recentThreshold = (state.stats.sync_freshness_thresholds && state.stats.sync_freshness_thresholds.recent_minutes) || 60;

  if (diffMinutes < 1) {
    return {
      status: 'fresh',
      text: '● Обновлено только что',
      className: 'freshness-fresh'
    };
  } else if (diffMinutes < freshThreshold) {
    return {
      status: 'fresh',
      text: '● Обновлено ' + diffMinutes + ' мин назад',
      className: 'freshness-fresh'
    };
  } else if (diffMinutes < recentThreshold) {
    return {
      status: 'recent',
      text: '● Обновлено ' + diffMinutes + ' мин назад',
      className: 'freshness-recent'
    };
  } else {
    const hours = Math.floor(diffMinutes / 60);
    if (hours < 24) {
      return {
        status: 'stale',
        text: '⚠ Обновлено ' + hours + ' ч назад',
        className: 'freshness-stale'
      };
    } else {
      const days = Math.floor(hours / 24);
      return {
        status: 'stale',
        text: '⚠ Обновлено ' + days + ' дн назад',
        className: 'freshness-stale'
      };
    }
  }
}

function updateCurrentDateDisplay() {
  const lbl = document.getElementById('focus-date-label');
  const badge = document.getElementById('focus-meta-badge');
  const now = new Date();
  const options = { weekday: 'long', day: 'numeric', month: 'long' };
  const str = now.toLocaleDateString('ru-RU', options);
  if (lbl) {
    const formattedDate = str.charAt(0).toUpperCase() + str.slice(1);
    const freshness = getFreshnessInfo();
    lbl.innerHTML = escapeHtml(formattedDate) + ' <span class="data-freshness-pill ' + freshness.className + '" id="data-freshness-pill" title="Состояние синхронизации">' + escapeHtml(freshness.text) + '</span>';
  }
  if (badge) {
    badge.textContent = '5108 · 2 п/г · ' + (state.scheduleParity === 'чет' ? 'Четная' : 'Нечетная') + ' неделя';
  }
}

function updateFreshnessDisplay() {
  const pill = document.getElementById('data-freshness-pill');
  if (pill) {
    const freshness = getFreshnessInfo();
    pill.className = 'data-freshness-pill ' + freshness.className;
    pill.textContent = freshness.text;
  } else {
    updateCurrentDateDisplay();
  }
}

function setupThemeToggle() {
  const btn = document.getElementById('theme-toggle-btn');
  const icon = document.getElementById('theme-toggle-icon');
  const metaTheme = document.querySelector('meta[name="theme-color"]');

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('kai_theme', theme);
    if (metaTheme) {
      metaTheme.setAttribute('content', theme === 'light' ? '#f2f4f8' : '#0b0d13');
    }
    if (icon) {
      if (theme === 'light') {
        // Moon icon for light theme (clicking switches to dark)
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
        if (btn) btn.setAttribute('title', 'Включить тёмную тему');
      } else {
        // Sun icon for dark theme (clicking switches to light)
        icon.innerHTML = '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
        if (btn) btn.setAttribute('title', 'Включить светлую тему');
      }
    }
  }

  // Initial theme detection from localStorage or system preference
  const saved = localStorage.getItem('kai_theme');
  const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  const initialTheme = saved || (prefersLight ? 'light' : 'dark');
  applyTheme(initialTheme);

  if (btn) {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
      showToast(nextTheme === 'light' ? 'Включена светлая тема' : 'Включена тёмная тема');
    });
  }
}

function setupTopBarEvents() {
  const parityBtn = document.getElementById('parity-toggle-btn');
  if (parityBtn) {
    parityBtn.addEventListener('click', () => {
      state.scheduleParity = state.scheduleParity === 'чет' ? 'нечет' : 'чет';
      const parityLabel = document.getElementById('parity-label');
      if (parityLabel) parityLabel.textContent = state.scheduleParity === 'чет' ? 'Чёт' : 'Нечёт';
      const schedParityBadge = document.getElementById('schedule-parity-badge');
      if (schedParityBadge) schedParityBadge.textContent = (state.scheduleParity === 'чет' ? 'Чётная' : 'Нечётная') + ' неделя';
      updateCurrentDateDisplay();
      showToast('Расписание: ' + state.scheduleParity + ' неделя');
      loadScheduleData();
      loadTodayScheduleForLive();
    });
  }

  const refreshBtn = document.getElementById('global-refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      showToast('Очистка кэша и обновление...');
      if ('caches' in window) {
        try {
          const keys = await caches.keys();
          await Promise.all(keys.map((k) => caches.delete(k)));
        } catch (e) {}
      }
      if ('serviceWorker' in navigator) {
        try {
          const regs = await navigator.serviceWorker.getRegistrations();
          for (const reg of regs) await reg.update();
        } catch (e) {}
      }
      await initAppData();
      showToast('Данные успешно обновлены!');
    });
  }
}

function setupNavigation() {
  // Mobile dock tabs
  const dockButtons = document.querySelectorAll('.liquid-bottom-dock .dock-tab');
  dockButtons.forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Desktop nav tabs
  const deskButtons = document.querySelectorAll('.desktop-nav .desktop-nav-btn');
  deskButtons.forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tabName) {
  state.currentTab = tabName;

  // Update active state in mobile dock
  document.querySelectorAll('.liquid-bottom-dock .dock-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  // Update active state in desktop nav
  document.querySelectorAll('.desktop-nav .desktop-nav-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  // Update visible view
  document.querySelectorAll('.app-view').forEach((view) => {
    const isTarget = view.id === 'view-' + tabName;
    view.classList.toggle('active', isTarget);
  });

  if (tabName === 'focus') {
    renderFocusView();
  } else if (tabName === 'tasks') {
    renderTasksMainView();
  } else if (tabName === 'ai') {
    const aiInput = document.getElementById('gemini-text-input');
    if (aiInput) setTimeout(() => aiInput.focus(), 150);
  } else if (tabName === 'more') {
    loadScheduleData();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// -------------------------------------------------------------
// TAB 1: СЕГОДНЯ (FOCUS VIEW)
// -------------------------------------------------------------
function renderFocusView() {
  updateCurrentDateDisplay();
  updateLiveLessonStatus();
  renderNextActionCard();
  renderUrgentTasksCard();
  renderTodaySchedulePeek();
  renderProgressOverviewCard();
}

async function loadTodayScheduleForLive() {
  const day = new Date().getDay();
  if (day === 0) {
    state.todaySchedule = [];
    updateLiveLessonStatus();
    renderTodaySchedulePeek();
    return;
  }
  try {
    const res = await apiFetch(API_BASE + '/api/schedule?day=' + day + '&week=' + state.scheduleParity);
    if (res.ok) {
      const data = await res.json();
      state.todaySchedule = data.lessons || [];
      updateLiveLessonStatus();
      renderTodaySchedulePeek();
    }
  } catch (e) {
    console.error('Failed to load today schedule for live hero:', e);
  }
}

function updateLiveLessonStatus() {
  const badge = document.getElementById('hero-status-badge');
  const statusText = document.getElementById('hero-status-text');
  const timeSlot = document.getElementById('hero-time-slot');
  const title = document.getElementById('hero-lesson-title');
  const bldgChip = document.getElementById('hero-building-chip');
  const teacherText = document.getElementById('hero-teacher-text');
  const progressWrapper = document.getElementById('hero-progress-wrapper');
  const progressFill = document.getElementById('hero-progress-fill');
  const timeLeftLabel = document.getElementById('hero-progress-time-left');
  const percentLabel = document.getElementById('hero-progress-percent');

  if (!badge || !title) return;

  const now = new Date();
  const currentDay = now.getDay();
  const currentMin = now.getHours() * 60 + now.getMinutes();

  if (currentDay === 0) {
    badge.className = 'status-pulse-capsule live-done';
    statusText.textContent = 'Выходной день';
    timeSlot.textContent = 'Отдых';
    title.textContent = 'Пар сегодня нет';
    bldgChip.className = 'hero-chip building-chip bldg-2';
    bldgChip.textContent = 'ИРЭФ-ЦТ';
    teacherText.textContent = 'Набирайся сил перед новой учебной неделей!';
    if (progressWrapper) progressWrapper.style.display = 'none';
    return;
  }

  if (!state.todaySchedule || state.todaySchedule.length === 0) {
    badge.className = 'status-pulse-capsule live-done';
    statusText.textContent = 'Свободный день';
    timeSlot.textContent = 'Нет пар';
    title.textContent = 'Занятий по расписанию нет';
    bldgChip.className = 'hero-chip building-chip bldg-2';
    bldgChip.textContent = 'Группа 5108';
    teacherText.textContent = 'Отличный день для закрытия долгов и лабораторных!';
    if (progressWrapper) progressWrapper.style.display = 'none';
    return;
  }

  const sorted = [...state.todaySchedule]
    .map((l) => ({ lesson: l, range: getLessonTimeRange(l) }))
    .sort((a, b) => a.range.startMin - b.range.startMin);

  // 1. Check if currently active lesson
  for (const item of sorted) {
    const { lesson, range } = item;
    if (currentMin >= range.startMin && currentMin < range.endMin) {
      badge.className = 'status-pulse-capsule live-active';
      statusText.textContent = 'Сейчас идет пара';
      timeSlot.textContent = range.formatted;
      const typePrefix = lesson.discipl_type ? '[' + lesson.discipl_type + '] ' : '';
      title.textContent = typePrefix + lesson.discipl_name;
      const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
      bldgChip.className = 'hero-chip building-chip ' + chip.cls;
      bldgChip.textContent = chip.label;
      teacherText.textContent = formatTeacherName(lesson.prepod_name || 'Преподаватель не указан');

      if (progressWrapper) {
        progressWrapper.style.display = 'block';
        const duration = range.endMin - range.startMin;
        const elapsed = currentMin - range.startMin;
        const pct = Math.min(100, Math.max(0, Math.round((elapsed / duration) * 100)));
        const rem = range.endMin - currentMin;
        progressFill.style.width = pct + '%';
        timeLeftLabel.textContent = 'Осталось: ' + rem + ' мин';
        percentLabel.textContent = pct + '%';
      }
      return;
    }
  }

  // 2. Check if before next lesson
  for (let i = 0; i < sorted.length; i++) {
    const { lesson, range } = sorted[i];
    if (currentMin < range.startMin) {
      const waitMin = range.startMin - currentMin;
      const isFirstLesson = (i === 0);
      badge.className = 'status-pulse-capsule live-break';
      statusText.textContent = isFirstLesson ? ('До первой пары ' + waitMin + ' мин') : ('До пары ' + waitMin + ' мин');
      timeSlot.textContent = 'Старт в ' + range.startStr;
      const typePrefix = lesson.discipl_type ? '[' + lesson.discipl_type + '] ' : '';
      title.textContent = typePrefix + lesson.discipl_name;
      const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
      bldgChip.className = 'hero-chip building-chip ' + chip.cls;
      bldgChip.textContent = chip.label;
      teacherText.textContent = formatTeacherName(lesson.prepod_name || 'Преподаватель не указан');

      if (progressWrapper) {
        progressWrapper.style.display = 'block';
        progressFill.style.width = '0%';
        timeLeftLabel.textContent = isFirstLesson ? ('До начала занятий: ' + waitMin + ' мин') : ('Перемена: ' + waitMin + ' мин');
        percentLabel.textContent = isFirstLesson ? 'Утро' : 'Скоро';
      }
      return;
    }
  }

  // 3. All lessons completed
  badge.className = 'status-pulse-capsule live-done';
  statusText.textContent = 'Пары завершены';
  timeSlot.textContent = 'Свободен';
  title.textContent = 'Учебный день завершен!';
  bldgChip.className = 'hero-chip building-chip bldg-2';
  bldgChip.textContent = 'Отдых';
  teacherText.textContent = 'Все пары на сегодня благополучно завершены';
  if (progressWrapper) progressWrapper.style.display = 'none';
}

// 2. Next Action Block
function renderNextActionCard() {
  const titleEl = document.getElementById('next-action-title');
  const timeEl = document.getElementById('next-action-time');
  const btnEl = document.getElementById('next-action-btn');
  if (!titleEl || !timeEl) return;

  const actionable = state.tasks.filter((t) => !isReferenceMaterial(t) && t.status === 'todo');

  if (actionable.length === 0) {
    titleEl.textContent = 'Все долги закрыты!';
    timeEl.textContent = 'Отличная работа, можно отдохнуть или повторить лекции';
    if (btnEl) btnEl.style.display = 'none';
    return;
  }

  // Find most urgent (deadline priority or first undone)
  const sorted = [...actionable].sort((a, b) => {
    if (a.deadline && !b.deadline) return -1;
    if (!a.deadline && b.deadline) return 1;
    return 0;
  });

  const nextTask = sorted[0];
  titleEl.textContent = (nextTask.subject_name ? nextTask.subject_name + ' — ' : '') + nextTask.title;

  if (nextTask.deadline) {
    timeEl.innerHTML = '<span class="text-coral">' + escapeHtml(formatDeadlineDisplay(nextTask.deadline)) + '</span>';
  } else {
    timeEl.textContent = (nextTask.task_type || 'Лабораторная работа') + ' · Требуется сдача';
  }

  if (btnEl) {
    btnEl.style.display = 'inline-flex';
    btnEl.onclick = () => {
      openTaskDetailSheet(nextTask.id);
    };
  }
}

// 3. Urgent Tasks Surface
function renderUrgentTasksCard() {
  const container = document.getElementById('urgent-tasks-container');
  if (!container) return;

  const actionable = state.tasks.filter((t) => !isReferenceMaterial(t));
  const pending = actionable.filter((t) => t.status === 'todo');

  if (pending.length === 0) {
    container.innerHTML = '<div class="empty-state-card">' +
      '<div class="empty-state-icon">' +
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>' +
          '<polyline points="22 4 12 14.01 9 11.01"></polyline>' +
        '</svg>' +
      '</div>' +
      '<div class="empty-state-title">Все лабораторные сданы</div>' +
      '<div class="empty-state-sub">Долгов нет. Отличная работа!</div>' +
    '</div>';
    return;
  }

  const urgent = pending.slice(0, 3);
  container.innerHTML = urgent
    .map((task) => {
      const deadlineStr = task.deadline ? formatDeadlineDisplay(task.deadline) : (task.deadline_raw || '');
      const deadlineMarkup = deadlineStr
        ? '<span class="urgent-task-deadline">' + escapeHtml(deadlineStr) + '</span>'
        : '';

      return '<div class="urgent-task-item" id="urgent-item-' + task.id + '" data-task-id="' + task.id + '" style="cursor: pointer;">' +
        '<div class="urgent-task-left">' +
          '<button class="task-checkbox-hit-area" data-task-id="' + task.id + '" title="Отметить как сданное" aria-label="Отметить">' +
            '<span class="custom-checkbox">' +
              '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>' +
            '</span>' +
          '</button>' +
          '<div style="min-width:0; flex:1;">' +
            '<div class="urgent-task-title">' + escapeHtml(task.title) + '</div>' +
            '<div class="urgent-task-sub-row">' +
              '<span class="urgent-task-sub">' + escapeHtml(task.subject_name) + '</span>' +
              (deadlineMarkup ? '<span class="meta-dot">·</span>' + deadlineMarkup : '') +
            '</div>' +
          '</div>' +
        '</div>' +
        '<span class="urgent-badge">' + escapeHtml(task.task_type || 'Лаб') + '</span>' +
      '</div>';
    })
    .join('');

  container.querySelectorAll('.urgent-task-item').forEach((item) => {
    item.addEventListener('click', (e) => {
      if (e.target.closest('.task-checkbox-hit-area')) return;
      const tid = parseInt(item.dataset.taskId, 10);
      openTaskDetailSheet(tid);
    });
  });

  container.querySelectorAll('.task-checkbox-hit-area, .custom-checkbox').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tid = parseInt(btn.dataset.taskId, 10);
      handleTaskToggle(tid);
    });
  });
}

// 4. Schedule Today Peek (Mobile Timeline Agenda)
function renderTodaySchedulePeek() {
  const container = document.getElementById('today-peek-container');
  if (!container) return;

  if (!state.todaySchedule || state.todaySchedule.length === 0) {
    container.innerHTML = '<div class="empty-state-card">' +
      '<div class="empty-state-icon">' +
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>' +
          '<line x1="16" y1="2" x2="16" y2="6"></line>' +
          '<line x1="8" y1="2" x2="8" y2="6"></line>' +
          '<line x1="3" y1="10" x2="21" y2="10"></line>' +
        '</svg>' +
      '</div>' +
      '<div class="empty-state-title">Сегодня пар нет</div>' +
      '<div class="empty-state-sub">Для 2-й подгруппы пары не запланированы</div>' +
    '</div>';
    return;
  }

  const lessons = state.todaySchedule.slice(0, 5);
  let html = '';
  lessons.forEach((l) => {
    const range = getLessonTimeRange(l);
    const chip = getBuildingBadge(l.build_num, l.aud_num);
    const tLower = (l.discipl_type || '').toLowerCase();
    let stripeClass = 'practice';
    if (tLower.includes('лаб')) stripeClass = 'lab';
    else if (tLower.includes('лекц')) stripeClass = 'lecture';

    html += '<div class="timeline-agenda-row">' +
      '<div class="timeline-time-col">' +
        '<span class="timeline-time-start">' + range.startStr + '</span>' +
        '<span class="timeline-time-end">' + range.endStr + '</span>' +
      '</div>' +
      '<div class="timeline-stripe ' + stripeClass + '"></div>' +
      '<div class="timeline-info-col">' +
        '<div class="timeline-lesson-title">' + escapeHtml(l.discipl_name) + '</div>' +
        '<div class="timeline-meta-row">' +
          '<span>' + escapeHtml(l.discipl_type || 'Пара') + '</span>' +
          '<span>·</span>' +
          '<span>' + chip.label + '</span>' +
          (l.prepod_name ? '<span>·</span><span>' + escapeHtml(formatTeacherName(l.prepod_name)) + '</span>' : '') +
        '</div>' +
      '</div>' +
    '</div>';
  });
  container.innerHTML = html;
}

// 5. Home Inline AI Composer
function setupHomeComposerEvents() {
  const homeInput = document.getElementById('home-ai-input');
  const homeSendBtn = document.getElementById('home-ai-send-btn');
  const homeMicBtn = document.getElementById('home-ai-mic-btn');

  // Suggestion buttons on home
  document.querySelectorAll('.liquid-glass-composer .pill-suggestion').forEach((btn) => {
    btn.addEventListener('click', () => {
      const prompt = btn.dataset.prompt;
      if (homeInput && prompt) {
        homeInput.value = prompt;
        homeInput.focus();
      }
    });
  });

  if (homeSendBtn) {
    homeSendBtn.addEventListener('click', () => {
      const text = homeInput ? homeInput.value.trim() : '';
      if (!text) {
        showToast('Введите или надиктуйте текст задачи');
        return;
      }
      // Transfer text to AI tab input and switch tab
      const aiInput = document.getElementById('gemini-text-input');
      if (aiInput) {
        aiInput.value = text;
        aiInput.style.height = 'auto';
        aiInput.style.height = Math.max(72, aiInput.scrollHeight) + 'px';
      }
      switchTab('ai');
      // Trigger AI parsing automatically
      const submitBtn = document.getElementById('gemini-submit-btn');
      if (submitBtn) submitBtn.click();
    });
  }

  // Home mic dictation
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition && homeMicBtn) {
    try {
      const recog = new SpeechRecognition();
      recog.lang = 'ru-RU';
      recog.continuous = false;

      recog.onstart = () => {
        homeMicBtn.classList.add('recording');
        showToast('Слушаю, говорите...');
      };
      recog.onresult = (e) => {
        const tr = e.results[0][0].transcript;
        if (homeInput) {
          homeInput.value = homeInput.value ? homeInput.value + ' ' + tr : tr;
        }
        showToast('Распознано: ' + tr);
      };
      recog.onend = () => {
        homeMicBtn.classList.remove('recording');
      };
      recog.onerror = (e) => {
        homeMicBtn.classList.remove('recording');
        showToast('Ошибка микрофона: ' + (e.error || ''));
      };

      homeMicBtn.addEventListener('click', () => {
        try {
          recog.start();
        } catch (err) {
          recog.stop();
        }
      });
    } catch (e) {
      console.warn('SpeechRecognition error on home:', e);
    }
  } else if (homeMicBtn) {
    homeMicBtn.addEventListener('click', () => {
      showToast('Голосовой ввод не поддерживается браузером');
    });
  }
}

// 6. Semester Progress Overview
function renderProgressOverviewCard() {
  const actionable = state.tasks.filter((t) => !isReferenceMaterial(t));
  const total = actionable.length;
  const done = actionable.filter((t) => t.status === 'done').length;
  const todo = total - done;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const ringFill = document.getElementById('focus-ring-fill');
  const ringPct = document.getElementById('focus-ring-percent');
  const statDone = document.getElementById('focus-stat-done');
  const statTodo = document.getElementById('focus-stat-todo');
  const statTotal = document.getElementById('focus-stat-total');
  const badge = document.getElementById('bento-motivation-badge');

  if (ringFill) {
    const circumference = 314.159;
    const offset = circumference - (circumference * pct) / 100;
    ringFill.style.strokeDashoffset = offset;
  }
  if (ringPct) ringPct.textContent = pct + '%';
  if (statDone) statDone.textContent = done;
  if (statTodo) statTodo.textContent = todo;
  if (statTotal) statTotal.textContent = total;

  if (badge) {
    if (pct === 100) badge.textContent = 'Все работы сданы';
    else if (pct >= 75) badge.textContent = 'Финишная прямая';
    else if (pct >= 50) badge.textContent = 'Больше половины';
    else if (pct >= 25) badge.textContent = 'Хороший темп';
    else badge.textContent = 'В начале пути';
  }
}

// -------------------------------------------------------------
// TAB 2: ЗАДАНИЯ (TASKS VIEW)
// -------------------------------------------------------------
function setupSegmentControl() {
  const btnSub = document.getElementById('tab-btn-submissions');
  const btnMat = document.getElementById('tab-btn-materials');
  const statusRow = document.getElementById('tasks-status-row');

  if (btnSub && btnMat) {
    btnSub.addEventListener('click', () => {
      state.currentSegment = 'submissions';
      btnSub.classList.add('active');
      btnMat.classList.remove('active');
      if (statusRow) statusRow.style.display = 'flex';
      renderTasksMainView();
    });

    btnMat.addEventListener('click', () => {
      state.currentSegment = 'materials';
      btnMat.classList.add('active');
      btnSub.classList.remove('active');
      if (statusRow) statusRow.style.display = 'none';
      renderTasksMainView();
    });
  }
}

function setupTasksEvents() {
  const chips = document.querySelectorAll('#tasks-status-row .status-capsule');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      state.tasksStatusFilter = chip.dataset.status;
      chips.forEach((c) => c.classList.toggle('active', c.dataset.status === state.tasksStatusFilter));
      renderTasksMainView();
    });
  });

  const searchInput = document.getElementById('task-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.toLowerCase().trim();
      renderTasksMainView();
    });
  }
}

async function loadTasksData() {
  try {
    const [tasksRes, subjRes] = await Promise.all([
      apiFetch(API_BASE + '/api/tasks'),
      apiFetch(API_BASE + '/api/subjects')
    ]);
    if (tasksRes.ok) state.tasks = await tasksRes.json();
    if (subjRes.ok) state.subjects = await subjRes.json();
    updateBadges();
    renderSubjectFilterChips();
  } catch (e) {
    console.error('Failed to load tasks data:', e);
  }
}

async function loadStatsData() {
  try {
    const res = await apiFetch(API_BASE + '/api/stats');
    if (res.ok) {
      state.stats = await res.json();
      updateFreshnessDisplay();
    }
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

function updateBadges() {
  const actionable = state.tasks.filter((t) => !isReferenceMaterial(t));
  const pendingCount = actionable.filter((t) => t.status === 'todo').length;
  const materialsCount = state.tasks.filter((t) => isReferenceMaterial(t)).length;

  const subBadge = document.getElementById('count-submissions-badge');
  if (subBadge) subBadge.textContent = pendingCount;

  const matBadge = document.getElementById('count-materials-badge');
  if (matBadge) matBadge.textContent = materialsCount;

  const bottomBadge = document.getElementById('bottom-todo-badge');
  if (bottomBadge) {
    bottomBadge.textContent = pendingCount;
    bottomBadge.style.display = pendingCount > 0 ? 'block' : 'none';
  }
}

function renderSubjectFilterChips() {
  const container = document.getElementById('subject-filter-chips');
  if (!container) return;

  let html = '<button class="subject-chip ' + (state.tasksSubjectFilter === 0 ? 'active' : '') + '" data-subject-id="0">Все курсы (' + state.subjects.length + ')</button>';

  state.subjects.forEach((subj) => {
    const isActive = state.tasksSubjectFilter === subj.id;
    html += '<button class="subject-chip ' + (isActive ? 'active' : '') + '" data-subject-id="' + subj.id + '">' + escapeHtml(subj.name) + '</button>';
  });

  container.innerHTML = html;

  container.querySelectorAll('.subject-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      state.tasksSubjectFilter = parseInt(chip.dataset.subjectId, 10);
      container.querySelectorAll('.subject-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      renderTasksMainView();
    });
  });
}

function renderTasksMainView() {
  const container = document.getElementById('tasks-main-container');
  if (!container) return;

  const isSubmissions = state.currentSegment === 'submissions';

  let list = state.tasks.filter((t) => {
    const isRef = isReferenceMaterial(t);
    return isSubmissions ? !isRef : isRef;
  });

  if (isSubmissions && state.tasksStatusFilter !== 'all') {
    list = list.filter((t) => t.status === state.tasksStatusFilter);
  }

  if (state.tasksSubjectFilter !== 0) {
    list = list.filter((t) => t.subject_id === state.tasksSubjectFilter);
  }

  if (state.searchQuery) {
    const q = state.searchQuery;
    list = list.filter((t) => {
      const matchTitle = (t.title || '').toLowerCase().includes(q);
      const matchSubj = (t.subject_name || '').toLowerCase().includes(q);
      return matchTitle || matchSubj;
    });
  }

  if (list.length === 0) {
    container.innerHTML = '<div class="empty-state-card">' +
      '<div class="empty-state-icon">' +
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<circle cx="11" cy="11" r="8"></circle>' +
          '<line x1="21" y1="21" x2="16.65" y2="16.65"></line>' +
        '</svg>' +
      '</div>' +
      '<div class="empty-state-title">Ничего не найдено</div>' +
      '<div class="empty-state-sub">Измените параметры поиска или фильтр курса</div>' +
    '</div>';
    return;
  }

  const grouped = new Map();
  list.forEach((item) => {
    const sid = item.subject_id;
    if (!grouped.has(sid)) {
      grouped.set(sid, {
        subject_id: sid,
        subject_name: item.subject_name,
        items: []
      });
    }
    grouped.get(sid).items.push(item);
  });

  let html = '';
  for (const group of grouped.values()) {
    const totalInGroup = group.items.length;
    const doneInGroup = group.items.filter((i) => i.status === 'done').length;
    const pct = totalInGroup > 0 ? Math.round((doneInGroup / totalInGroup) * 100) : 0;

    const countPillText = isSubmissions
      ? doneInGroup + '/' + totalInGroup + ' сдано'
      : totalInGroup + ' файлов';

    html += '<div class="course-accordion-card glass-subtle" data-subject-id="' + group.subject_id + '">' +
      '<div class="course-header" data-subject-id="' + group.subject_id + '">' +
        '<div class="course-header-top">' +
          '<div class="course-title-block">' +
            '<span class="course-accordion-chevron">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="6 9 12 15 18 9"></polyline>' +
              '</svg>' +
            '</span>' +
            '<h3 class="course-title">' + escapeHtml(group.subject_name) + '</h3>' +
          '</div>' +
          '<span class="course-count-pill">' + countPillText + '</span>' +
        '</div>' +
        (isSubmissions ? '<div class="course-progress-bar"><div class="course-progress-fill" style="width: ' + pct + '%"></div></div>' : '') +
      '</div>' +
      '<div class="course-items-body">' +
        group.items.map((item) => (isSubmissions ? renderActionableTaskRow(item) : renderMaterialDocRow(item))).join('') +
      '</div>' +
    '</div>';
  }

  container.innerHTML = html;

  if (!container.__hasDelegatedEvents) {
    container.__hasDelegatedEvents = true;
    container.addEventListener('click', (e) => {
      const chk = e.target.closest('.task-checkbox-hit-area, .custom-checkbox');
      if (chk && chk.dataset.taskId) {
        e.stopPropagation();
        const tid = parseInt(chk.dataset.taskId, 10);
        if (!isNaN(tid)) handleTaskToggle(tid);
        return;
      }

      const row = e.target.closest('.task-row, .doc-card');
      if (row && row.dataset.taskId) {
        const tid = parseInt(row.dataset.taskId, 10);
        if (!isNaN(tid)) openTaskDetailSheet(tid);
        return;
      }

      const hdr = e.target.closest('.course-header');
      if (hdr) {
        toggleAccordion(hdr);
        return;
      }
    });
  }
}

function renderActionableTaskRow(task) {
  const isDone = task.status === 'done';
  const hasFiles = Boolean(task.file_url || (task.attachments && task.attachments.length > 0));

  const fileIndicator = hasFiles
    ? '<span class="task-file-indicator" title="Прикреплены материалы">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>' +
      '</span>'
    : '';

  return '<div class="task-row ' + (isDone ? 'is-done' : '') + '" id="task-row-' + task.id + '" data-task-id="' + task.id + '" style="cursor: pointer;">' +
    '<button class="task-checkbox-hit-area" data-task-id="' + task.id + '" title="Изменить статус" aria-label="Изменить статус">' +
      '<span class="custom-checkbox">' +
        '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>' +
      '</span>' +
    '</button>' +
    '<div class="task-info">' +
      '<div class="task-title-text">' + escapeHtml(task.title) + '</div>' +
      '<div class="task-badges">' +
        '<span class="mini-badge mini-lab">' + escapeHtml(task.task_type || 'Лаб') + '</span>' +
        (task.deadline ? '<span class="mini-badge mini-deadline">' + escapeHtml(formatDeadlineDisplay(task.deadline)) + '</span>' : '') +
        fileIndicator +
      '</div>' +
    '</div>' +
    '<div class="task-row-chevron">' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>' +
    '</div>' +
  '</div>';
}

function renderMaterialDocRow(task) {
  const hasFiles = Boolean(task.file_url || (task.attachments && task.attachments.length > 0));
  const docFileName = escapeHtml(task.file_name || task.title || 'Материалы');
  const bbUrl = task.external_url || task.bb_course_url || 'https://bb.kai.ru';

  const geminiDocBtn = '<button class="doc-open-btn btn-gemini-summary glass-control" data-task-id="' + task.id + '" title="AI-разбор">' +
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
      '<span>Разбор</span>' +
    '</button>';

  const downloadBtn = hasFiles
    ? '<button type="button" class="doc-open-btn download-btn glass-control" onclick="downloadTaskFile(' + task.id + ', null, \'' + docFileName + '\')" title="Скачать файл">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
        '<span>Скачать</span>' +
      '</button>'
    : '<span class="doc-nofile">Без файла</span>';

  const bbBtn = '<a href="' + bbUrl + '" target="_blank" rel="noopener noreferrer" class="doc-open-btn doc-bb-btn glass-control" title="Открыть в Blackboard">' +
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>' +
      '<span>В BB</span>' +
    '</a>';

  return '<div class="doc-card">' +
    '<div class="doc-left">' +
      '<div class="doc-icon-box">' +
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>' +
          '<polyline points="14 2 14 8 20 8"></polyline>' +
          '<line x1="16" y1="13" x2="8" y2="13"></line>' +
          '<line x1="16" y1="17" x2="8" y2="17"></line>' +
          '<polyline points="10 9 9 9 8 9"></polyline>' +
        '</svg>' +
      '</div>' +
      '<div style="min-width: 0; flex: 1;">' +
        '<div class="doc-title">' + escapeHtml(task.title) + '</div>' +
      '</div>' +
    '</div>' +
    '<div class="doc-actions-row">' +
      geminiDocBtn +
      downloadBtn +
      bbBtn +
    '</div>' +
  '</div>';
}

function toggleAccordion(header) {
  const body = header.nextElementSibling;
  if (!body) return;
  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? 'flex' : 'none';
}

async function handleTaskToggle(taskId) {
  const task = state.tasks.find((t) => t.id === taskId);
  if (!task) return;

  const oldStatus = task.status;
  const newStatus = oldStatus === 'todo' ? 'done' : 'todo';
  task.status = newStatus;

  // 1. Immediately provide visual feedback in the current DOM
  const taskRow = document.getElementById('task-row-' + taskId);
  const urgentRow = document.querySelector('.urgent-task-item[data-task-id="' + taskId + '"]');

  [taskRow, urgentRow].forEach((row) => {
    if (row) {
      row.classList.toggle('is-done', newStatus === 'done');
      const chk = row.querySelector('.custom-checkbox');
      if (chk) chk.classList.toggle('checked', newStatus === 'done');
      if (newStatus === 'done') {
        row.classList.add('task-confirm-anim');
        if (chk) chk.classList.add('check-confirm');
      }
    }
  });

  showToast(
    newStatus === 'done'
      ? 'Работа отмечена как сданная'
      : 'Работа возвращена в список'
  );

  updateBadges();

  // 2. Allow 300ms for student to see checkmark confirmation before re-rendering list
  setTimeout(() => {
    renderUrgentTasksCard();
    renderNextActionCard();
    renderProgressOverviewCard();
    if (state.currentTab === 'tasks') renderTasksMainView();
  }, 300);

  try {
    const res = await apiFetch(API_BASE + '/api/tasks/' + taskId + '/toggle', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to toggle status');
    const updated = await res.json();
    task.status = updated.status;
  } catch (err) {
    task.status = oldStatus;
    updateBadges();
    renderUrgentTasksCard();
    renderNextActionCard();
    renderProgressOverviewCard();
    if (taskRow) taskRow.classList.toggle('is-done', oldStatus === 'done');
    if (urgentRow) urgentRow.classList.toggle('is-done', oldStatus === 'done');
    showToast('Ошибка сохранения на сервере');
  }
}

function goToTasksForDiscipline(disciplName) {
  const norm = disciplName.toLowerCase().replace(/[^a-zа-яё0-9]/gi, '');
  const matched = state.subjects.find((s) => {
    const sNorm = s.name.toLowerCase().replace(/[^a-zа-яё0-9]/gi, '');
    return sNorm.includes(norm) || norm.includes(sNorm);
  });

  state.currentSegment = 'submissions';
  const btnSub = document.getElementById('tab-btn-submissions');
  const btnMat = document.getElementById('tab-btn-materials');
  if (btnSub) btnSub.classList.add('active');
  if (btnMat) btnMat.classList.remove('active');
  const statusRow = document.getElementById('tasks-status-row');
  if (statusRow) statusRow.style.display = 'flex';

  if (matched) {
    state.tasksSubjectFilter = matched.id;
  }
  switchTab('tasks');
  showToast('Фильтр: ' + disciplName);
}

// -------------------------------------------------------------
// TAB 3: AI ASSISTANT STUDIO (GEMINI)
// -------------------------------------------------------------
// TAB 3: STUDENT OS AI (FLOATING GLASS COMPOSER & PREVIEW SHEET)
// -------------------------------------------------------------
function setupGeminiEvents() {
  const geminiText = document.getElementById('gemini-text-input');
  const geminiMicBtn = document.getElementById('gemini-mic-btn');
  const geminiSubmitBtn = document.getElementById('gemini-submit-btn');
  const geminiLoader = document.getElementById('gemini-shimmer-loader');
  const geminiResult = document.getElementById('gemini-result-card');

  // Auto-resize textarea as user types
  if (geminiText) {
    const autoResize = () => {
      geminiText.style.height = 'auto';
      geminiText.style.height = Math.max(72, geminiText.scrollHeight) + 'px';
      if (geminiSubmitBtn) {
        geminiSubmitBtn.disabled = !geminiText.value.trim();
      }
    };
    geminiText.addEventListener('input', autoResize);
  }

  // Quick suggestion chips
  document.querySelectorAll('.ai-quick-chip, .gemini-suggest-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.dataset.prompt;
      if (geminiText && prompt) {
        geminiText.value = prompt;
        geminiText.style.height = 'auto';
        geminiText.style.height = Math.max(72, geminiText.scrollHeight) + 'px';
        geminiText.focus();
        if (geminiSubmitBtn) geminiSubmitBtn.disabled = false;
      }
    });
  });

  // Web Speech API for voice dictation
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;

  if (SpeechRecognition && geminiMicBtn) {
    try {
      recognition = new SpeechRecognition();
      recognition.lang = 'ru-RU';
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        isListening = true;
        geminiMicBtn.classList.add('recording');
        showToast('Слушаю, говорите...');
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (geminiText) {
          geminiText.value = geminiText.value ? geminiText.value + ' ' + transcript : transcript;
          geminiText.style.height = 'auto';
          geminiText.style.height = Math.max(72, geminiText.scrollHeight) + 'px';
        }
        if (geminiSubmitBtn) geminiSubmitBtn.disabled = false;
        showToast('Распознано: ' + transcript);
      };

      recognition.onerror = (e) => {
        console.warn('Speech recognition error:', e);
        showToast('Ошибка микрофона: ' + (e.error || 'неизвестно'));
      };

      recognition.onend = () => {
        isListening = false;
        geminiMicBtn.classList.remove('recording');
      };

      geminiMicBtn.addEventListener('click', () => {
        if (isListening) {
          recognition.stop();
        } else {
          try {
            recognition.start();
          } catch (err) {
            console.warn('SpeechRecognition start failed:', err);
          }
        }
      });
    } catch (err) {
      console.warn('Could not initialize SpeechRecognition:', err);
    }
  } else if (geminiMicBtn) {
    geminiMicBtn.addEventListener('click', () => {
      showToast('Голосовой ввод не поддерживается данным браузером');
    });
  }

  // Parse task with Student OS AI (Structured Preview & Confirm Flow)
  if (geminiSubmitBtn) {
    geminiSubmitBtn.addEventListener('click', async () => {
      const text = geminiText ? geminiText.value.trim() : '';
      if (!text) {
        showToast('Введите текст задачи');
        return;
      }

      if (geminiLoader) geminiLoader.style.display = 'block';
      if (geminiResult) geminiResult.style.display = 'none';
      geminiSubmitBtn.disabled = true;

      try {
        const res = await apiFetch(API_BASE + '/api/ai/parse-task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const parseErr = new Error(errData.detail || 'AI временно недоступен');
          parseErr.errorData = errData.error || {};
          parseErr.metadata = errData.metadata || {};
          throw parseErr;
        }

        const taskPreview = await res.json();

        if (geminiResult) {
          // Count detected changes / parameters
          let detectedCount = 0;
          if (taskPreview.subject_name) detectedCount++;
          if (taskPreview.title) detectedCount++;
          if (taskPreview.deadline_iso || taskPreview.deadline_raw) detectedCount++;
          if (taskPreview.auditorium) detectedCount++;
          if (taskPreview.materials_summary || taskPreview.requirements) detectedCount++;

          let countLabel = 'Найдено 4 изменения';
          if (detectedCount === 1) countLabel = 'Найдено 1 изменение';
          else if (detectedCount >= 2 && detectedCount <= 4) countLabel = 'Найдено ' + detectedCount + ' изменения';
          else if (detectedCount >= 5) countLabel = 'Найдено ' + detectedCount + ' изменений';

          let deadlineVal = 'Не указан';
          let deadlineSub = '';
          if (taskPreview.deadline_iso) {
            try {
              const d = new Date(taskPreview.deadline_iso);
              deadlineVal = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
              deadlineSub = formatDeadlineDisplay(taskPreview.deadline_iso);
            } catch (e) {
              deadlineVal = taskPreview.deadline_raw || 'Не указан';
            }
          } else if (taskPreview.deadline_raw) {
            deadlineVal = taskPreview.deadline_raw;
          }

          const audVal = taskPreview.auditorium || '301';
          const matVal = taskPreview.materials_summary || (taskPreview.requirements ? taskPreview.requirements : '2 файла');

          let evidenceBlock = '';
          if (taskPreview.evidence) {
            const ev = taskPreview.evidence;
            evidenceBlock = '<div class="sheet-evidence-card">' +
              '<div class="sheet-evidence-header">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>' +
                '<span>Почему это определено так</span>' +
              '</div>' +
              '<div class="sheet-evidence-list">' +
                '<div class="sheet-evidence-row">' +
                  '<span class="evidence-tag">Предмет</span>' +
                  '<div class="evidence-body">' +
                    '<strong>' + escapeHtml((ev.subject && ev.subject.name) || taskPreview.subject_name || 'Дисциплина') + '</strong>' +
                    '<span class="evidence-detail">' + escapeHtml((ev.subject && ev.subject.label) || 'Сопоставлено с учебным планом') + (ev.subject && ev.subject.confidence_percent ? ' · ' + ev.subject.confidence_percent + '% уверенность' : '') + '</span>' +
                  '</div>' +
                '</div>' +
                '<div class="sheet-evidence-row">' +
                  '<span class="evidence-tag">Дедлайн</span>' +
                  '<div class="evidence-body">' +
                    '<strong>' + escapeHtml((ev.deadline && ev.deadline.resolved_display) || deadlineVal) + '</strong>' +
                    '<span class="evidence-detail">' + escapeHtml((ev.deadline && ev.deadline.label) || 'Срок выполнения') + '</span>' +
                  '</div>' +
                '</div>' +
                '<div class="sheet-evidence-row">' +
                  '<span class="evidence-tag">Аудитория</span>' +
                  '<div class="evidence-body">' +
                    '<strong>' + escapeHtml((ev.auditorium && ev.auditorium.value) || audVal) + '</strong>' +
                    '<span class="evidence-detail">' + escapeHtml((ev.auditorium && ev.auditorium.source_label) || 'Аудитория пары') + '</span>' +
                  '</div>' +
                '</div>' +
                '<div class="sheet-evidence-row">' +
                  '<span class="evidence-tag">Источник</span>' +
                  '<div class="evidence-body">' +
                    '<strong>' + escapeHtml((ev.source && ev.source.primary) || 'Сообщение старосты') + '</strong>' +
                    '<span class="evidence-detail">' + escapeHtml((ev.source && ev.source.summary) || 'Входящий контекст') + '</span>' +
                  '</div>' +
                '</div>' +
              '</div>' +
            '</div>';
          } else {
            evidenceBlock = '<div class="sheet-reasoning-box">' +
              '<div class="sheet-reasoning-header">' +
                '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>' +
                '<span>Почему это определено так</span>' +
              '</div>' +
              '<div class="sheet-reasoning-text">' + escapeHtml(reasoningText) + '</div>' +
            '</div>';
          }

          geminiResult.innerHTML = '<div class="ai-preview-sheet" id="ai-preview-sheet">' +
            '<div class="sheet-top-row">' +
              '<div class="sheet-badge">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
                '<span>' + countLabel + '</span>' +
              '</div>' +
              '<button class="sheet-close-btn" id="sheet-close-btn" title="Закрыть">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>' +
              '</button>' +
            '</div>' +
            '<div class="sheet-grid">' +
              '<div class="sheet-cell">' +
                '<span class="sheet-cell-label">' + escapeHtml(taskPreview.subject_name || 'Дисциплина') + '</span>' +
                '<span class="sheet-cell-value">' + escapeHtml(taskPreview.title || 'Лабораторная работа') + '</span>' +
                '<span class="sheet-cell-sub">' + escapeHtml(taskPreview.task_type || 'лабораторная') + '</span>' +
              '</div>' +
              '<div class="sheet-cell">' +
                '<span class="sheet-cell-label">Дедлайн</span>' +
                '<span class="sheet-cell-value">' + escapeHtml(deadlineVal) + '</span>' +
                (deadlineSub ? '<span class="sheet-cell-sub">' + escapeHtml(deadlineSub) + '</span>' : '') +
              '</div>' +
              '<div class="sheet-cell">' +
                '<span class="sheet-cell-label">Аудитория</span>' +
                '<span class="sheet-cell-value">' + escapeHtml(audVal) + '</span>' +
              '</div>' +
              '<div class="sheet-cell">' +
                '<span class="sheet-cell-label">Материалы</span>' +
                '<span class="sheet-cell-value">' + escapeHtml(matVal) + '</span>' +
              '</div>' +
            '</div>' +
            evidenceBlock +
            '<div class="sheet-actions">' +
              '<button id="sheet-confirm-btn" class="sheet-confirm-btn glass-control">' +
                '<span>Добавить всё</span>' +
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' +
              '</button>' +
              '<button id="sheet-cancel-btn" class="sheet-cancel-btn glass-control">Отмена</button>' +
            '</div>' +
          '</div>';

          geminiResult.style.display = 'block';
          setTimeout(() => {
            try {
              geminiResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } catch (_) {}
          }, 100);

          // Dismiss handlers (Task is NOT created)
          const closeBtn = document.getElementById('sheet-close-btn');
          const cancelBtn = document.getElementById('sheet-cancel-btn');
          const dismissSheet = () => {
            geminiResult.style.display = 'none';
            geminiResult.innerHTML = '';
            showToast('Создание задачи отменено');
          };
          if (closeBtn) closeBtn.addEventListener('click', dismissSheet);
          if (cancelBtn) cancelBtn.addEventListener('click', dismissSheet);

          // Confirm handler: Persists to DB
          const confirmBtn = document.getElementById('sheet-confirm-btn');
          if (confirmBtn) {
            confirmBtn.addEventListener('click', async () => {
              confirmBtn.disabled = true;
              confirmBtn.innerHTML = '<span>Добавление...</span>';

              try {
                const saveRes = await apiFetch(API_BASE + '/api/tasks', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    subject_name: taskPreview.subject_name,
                    title: taskPreview.title,
                    task_type: taskPreview.task_type,
                    deadline: taskPreview.deadline_iso,
                    deadline_raw: taskPreview.deadline_raw,
                    requirements: taskPreview.requirements || taskPreview.materials_summary || undefined,
                    source: 'manual_ai'
                  })
                });

                if (!saveRes.ok) {
                  const errData = await saveRes.json().catch(() => ({}));
                  throw new Error(errData.detail || 'Не удалось сохранить задачу');
                }

                const savedTask = await saveRes.json();

                geminiResult.innerHTML = '<div class="ai-success-sheet">' +
                    '<div class="success-sheet-header">' +
                      '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
                      '<span>Добавлено в Student OS</span>' +
                    '</div>' +
                    '<div class="success-sheet-title">' + escapeHtml(savedTask.title) + '</div>' +
                    '<div class="success-sheet-tags">' +
                      '<span class="subtle-badge">' + escapeHtml(savedTask.subject_name) + '</span>' +
                      '<span class="subtle-badge" style="color: var(--accent);">' + escapeHtml(savedTask.task_type || 'Задание') + '</span>' +
                      (taskPreview.auditorium ? '<span class="subtle-badge">Ауд. ' + escapeHtml(taskPreview.auditorium) + '</span>' : '') +
                    '</div>' +
                    '<button class="glass-action-btn success-goto-btn glass-control" onclick="switchTab(\'focus\')" style="margin-top: 14px; width: 100%; justify-content: center;">' +
                      '<span>Перейти на главный экран (Сегодня)</span>' +
                      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>' +
                    '</button>' +
                  '</div>';

                if (geminiText) {
                  geminiText.value = '';
                  geminiText.style.height = 'auto';
                }
                showToast('Добавлено в расписание и задачи');

                await Promise.all([loadTasksData(), loadStatsData()]);
                renderFocusView();
                if (state.currentTab === 'tasks') renderTasksMainView();

              } catch (saveErr) {
                console.error('Save task error:', saveErr);
                showToast('Ошибка сохранения: ' + saveErr.message);
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<span>Попробовать снова</span>';
              }
            });
          }
        }

      } catch (err) {
        console.error('Student OS AI parse failed:', err);
        const errData = err.errorData || {};
        const title = errData.title || 'AI временно недоступен';
        const reassurance = errData.reassurance || 'Это не повлияло на сохранённые задания.';
        const detail = errData.detail || err.message || 'Сервер AI временно недоступен. Повторите попытку.';

        if (geminiResult) {
          geminiResult.innerHTML = '<div class="ai-fallback-box" style="padding: 20px; border-radius: 16px; background: var(--surface-secondary); border: 1px solid var(--border); text-align: center; margin-top: 12px;">' +
              '<div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">' + escapeHtml(title) + '</div>' +
              '<div style="font-size: 0.88rem; font-weight: 500; color: var(--text-secondary); margin-bottom: 8px;">' + escapeHtml(reassurance) + '</div>' +
              '<div style="font-size: 0.82rem; color: var(--text-tertiary); margin-bottom: 14px;">' + escapeHtml(detail) + '</div>' +
              '<button id="gemini-retry-btn" class="glass-control" style="padding: 8px 18px; border-radius: 980px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; background: var(--surface-primary); border: 1px solid var(--border); color: var(--text-primary);">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>' +
                '<span>Повторить</span>' +
              '</button>' +
            '</div>';
          geminiResult.style.display = 'block';

          const retryBtn = document.getElementById('gemini-retry-btn');
          if (retryBtn && geminiSubmitBtn) {
            retryBtn.addEventListener('click', () => geminiSubmitBtn.click());
          }
        }
        showToast(title + '. ' + reassurance);
      } finally {
        if (geminiLoader) geminiLoader.style.display = 'none';
        if (geminiSubmitBtn) geminiSubmitBtn.disabled = false;
      }
    });
  }

  // Lab Summary Modal Events
  const labOverlay = document.getElementById('lab-summary-overlay');
  const labCloseBtn = document.getElementById('lab-summary-close-btn');

  function closeLabSummary() {
    if (labOverlay) labOverlay.classList.remove('active');
  }

  if (labCloseBtn) labCloseBtn.addEventListener('click', closeLabSummary);
  if (labOverlay) {
    labOverlay.addEventListener('click', (e) => {
      if (e.target === labOverlay) closeLabSummary();
    });
  }

  // Delegation for lab summary buttons
  document.body.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-gemini-summary');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();

    const taskId = parseInt(btn.dataset.taskId, 10);
    await openLabSummaryModal(taskId);
  });
}

async function openLabSummaryModal(taskId) {
  const labOverlay = document.getElementById('lab-summary-overlay');
  const labTitle = document.getElementById('lab-summary-title');
  const labBody = document.getElementById('lab-summary-body');

  if (!labOverlay || !labBody) return;

  const task = state.tasks.find((t) => t.id === taskId);
  if (labTitle) {
    labTitle.textContent = task ? task.title : 'Шпаргалка к работе';
  }

  labBody.innerHTML = '<div class="gemini-shimmer-card" style="margin: 0; padding: 18px;">' +
      '<div class="shimmer-content">' +
        '<svg class="gemini-spin-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">' +
          '<path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>' +
        '</svg>' +
        '<span>Gemini анализирует методические материалы и ход работы...</span>' +
      '</div>' +
    '</div>';

  labOverlay.classList.add('active');

  try {
    const res = await apiFetch(API_BASE + '/api/ai/summarize-task/' + taskId, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const errObj = new Error(err.error?.message || err.detail || 'AI временно недоступен');
      errObj.errorData = err.error || {};
      errObj.metadata = err.metadata || {};
      throw errObj;
    }
    const data = await res.json();

    const toBringList = Array.isArray(data.to_bring) ? data.to_bring : (data.to_bring ? [data.to_bring] : []);
    const toBringItems = toBringList.length > 0
      ? toBringList.map((item) => '<li>' + escapeHtml(item) + '</li>').join('')
      : '<li>Методические указания и тетрадь для записей</li>';

    const stepsList = Array.isArray(data.key_steps) ? data.key_steps : (data.key_steps ? [data.key_steps] : []);
    const stepsItems = stepsList.length > 0
      ? stepsList.map((step) => '<li>' + escapeHtml(step) + '</li>').join('')
      : '<li>Изучить теоретическую часть</li><li>Выполнить расчеты</li><li>Оформить отчет</li>';

    labBody.innerHTML = '<div class="summary-section-box">' +
        '<div class="summary-section-title">' +
          '<span>Суть работы</span>' +
        '</div>' +
        '<p class="summary-section-text">' + escapeHtml(data.summary || 'Нет краткого описания') + '</p>' +
      '</div>' +
      '<div class="summary-section-box">' +
        '<div class="summary-section-title">' +
          '<span>Что взять с собой</span>' +
        '</div>' +
        '<ul class="summary-checklist">' + toBringItems + '</ul>' +
      '</div>' +
      '<div class="summary-section-box">' +
        '<div class="summary-section-title">' +
          '<span>Порядок действий</span>' +
        '</div>' +
        '<ol class="summary-steps-list">' + stepsItems + '</ol>' +
      '</div>';
  } catch (err) {
    console.error('Failed to summarize lab:', err);
    const errData = err.errorData || {};
    const title = errData.title || 'AI временно недоступен';
    const reassurance = errData.reassurance || 'Это не повлияло на сохранённые задания.';
    const detail = errData.detail || 'Сервер генерации сейчас перегружен. Повторите попытку через мгновение.';
    const retryable = errData.retryable !== false;

    let actionBtn = '';
    if (retryable) {
      actionBtn = '<button id="btn-retry-lab-summary" class="glass-control" style="margin-top: 18px; display: inline-flex; align-items: center; gap: 8px; padding: 10px 22px; font-weight: 600; border-radius: 980px; cursor: pointer; border: 1px solid var(--border); background: var(--surface-primary); color: var(--text-primary); transition: all 0.2s ease;">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>' +
          '<span>Повторить</span>' +
        '</button>';
    }

    labBody.innerHTML = '<div class="ai-fallback-box" style="text-align: center; padding: 32px 16px;">' +
        '<div style="width: 48px; height: 48px; border-radius: 50%; background: var(--surface-secondary); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; color: var(--accent);">' +
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>' +
        '</div>' +
        '<h3 style="font-size: 1.15rem; font-weight: 700; margin: 0 0 6px 0; color: var(--text-primary);">' + escapeHtml(title) + '</h3>' +
        '<p style="font-size: 0.92rem; font-weight: 500; color: var(--text-secondary); margin: 0 0 10px 0;">' + escapeHtml(reassurance) + '</p>' +
        '<p style="font-size: 0.82rem; color: var(--text-tertiary); margin: 0 auto; max-width: 320px; line-height: 1.4;">' + escapeHtml(detail) + '</p>' +
        actionBtn +
      '</div>';

    const retryBtn = document.getElementById('btn-retry-lab-summary');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        openLabSummaryModal(taskId);
      });
    }
  }
}

// -------------------------------------------------------------
// TAB 4: ЕЩЁ (SCHEDULE TIMELINE & BLACKBOARD SYNC)
// -------------------------------------------------------------
function setupScheduleEvents() {
  const pills = document.querySelectorAll('#schedule-day-pills .day-pill');
  pills.forEach((pill) => {
    pill.addEventListener('click', () => {
      const day = parseInt(pill.dataset.day, 10);
      state.scheduleDay = day;
      pills.forEach((p) => p.classList.toggle('active', parseInt(p.dataset.day, 10) === day));
      loadScheduleData();
    });
  });
}

async function loadScheduleData() {
  const container = document.getElementById('timeline-list');
  const dayTitle = document.getElementById('schedule-day-title');
  const parityBadge = document.getElementById('schedule-parity-badge');

  if (dayTitle) dayTitle.textContent = RUSSIAN_WEEKDAYS[state.scheduleDay] || 'Расписание';
  if (parityBadge) parityBadge.textContent = (state.scheduleParity === 'чет' ? 'Чётная' : 'Нечётная') + ' неделя';

  document.querySelectorAll('#schedule-day-pills .day-pill').forEach((pill) => {
    pill.classList.toggle('active', parseInt(pill.dataset.day, 10) === state.scheduleDay);
  });

  if (!container) return;

  try {
    const res = await apiFetch(API_BASE + '/api/schedule?day=' + state.scheduleDay + '&week=' + state.scheduleParity);
    if (!res.ok) throw new Error('Schedule API error');
    const data = await res.json();
    renderTimeline(data.lessons || []);
  } catch (err) {
    container.innerHTML = '<div class="task-placeholder" style="color: var(--accent-red);">Ошибка загрузки расписания</div>';
  }
}

function renderTimeline(lessons) {
  const container = document.getElementById('timeline-list');
  if (!container) return;

  if (lessons.length === 0) {
    container.innerHTML = '<div class="empty-state-card">' +
      '<div class="empty-state-icon">' +
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>' +
          '<line x1="16" y1="2" x2="16" y2="6"></line>' +
          '<line x1="8" y1="2" x2="8" y2="6"></line>' +
          '<line x1="3" y1="10" x2="21" y2="10"></line>' +
        '</svg>' +
      '</div>' +
      '<div class="empty-state-title">В этот день занятий нет</div>' +
      '<div class="empty-state-sub">Для 2-й подгруппы пары не запланированы</div>' +
    '</div>';
    return;
  }

  let html = '';
  lessons.forEach((lesson) => {
    const timeInfo = getLessonTimeRange(lesson);
    const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
    const typeLower = (lesson.discipl_type || '').toLowerCase();
    let barClass = 'timeline-event-bar';
    if (typeLower.includes('лаб')) barClass += ' bar-lab';
    else if (typeLower.includes('пр')) barClass += ' bar-prac';
    else if (typeLower.includes('лек')) barClass += ' bar-lec';

    const homeworkBadge = lesson.todo_tasks_count > 0
      ? '<button type="button" class="timeline-debt-pill glass-control" data-discipl="' + escapeHtml(lesson.discipl_name) + '" title="Перейти к заданиям по дисциплине">' +
          '<span>' + lesson.todo_tasks_count + ' к сдаче</span>' +
          '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14M12 5l7 7-7 7"/></svg>' +
        '</button>'
      : '';

    html += '<div class="timeline-event-row">' +
      '<div class="timeline-time-col">' +
        '<span class="timeline-time-start">' + escapeHtml(timeInfo.startStr) + '</span>' +
        '<span class="timeline-time-end">' + escapeHtml(timeInfo.endStr) + '</span>' +
      '</div>' +
      '<div class="' + barClass + '"></div>' +
      '<div class="timeline-event-content">' +
        '<div class="timeline-event-header">' +
          '<h4 class="timeline-event-title">' + escapeHtml(lesson.discipl_name) + '</h4>' +
          '<div class="timeline-chips-row">' +
            '<span class="building-badge ' + chip.cls + '">' + chip.label + '</span>' +
            (lesson.discipl_type ? '<span class="building-badge">' + escapeHtml(lesson.discipl_type) + '</span>' : '') +
            homeworkBadge +
          '</div>' +
        '</div>' +
        '<div class="timeline-meta">' +
          '<span class="timeline-teacher">' + escapeHtml(formatTeacherName(lesson.prepod_name || 'Преподаватель не указан')) + '</span>' +
        '</div>' +
      '</div>' +
    '</div>';
  });

  container.innerHTML = html;

  container.querySelectorAll('.timeline-debt-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      goToTasksForDiscipline(btn.dataset.discipl);
    });
  });
}

// Blackboard Sync
function setupSyncEvents() {
  const syncBtn = document.getElementById('bb-sync-btn');
  const syncText = document.getElementById('sync-btn-text');
  const syncTrack = document.getElementById('sync-progress-track');
  const syncBar = document.getElementById('sync-progress-bar');

  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      if (state.isSyncing) return;
      state.isSyncing = true;
      syncBtn.classList.add('is-loading');
      if (syncText) syncText.textContent = 'Синхронизация...';

      if (syncTrack && syncBar) {
        syncTrack.classList.add('active');
        syncBar.style.width = '20%';
      }

      showToast('Запущен сбор заданий с bb.kai.ru...');

      const progTimer = setInterval(() => {
        if (!state.isSyncing || !syncBar) return;
        const cur = parseFloat(syncBar.style.width) || 20;
        if (cur < 85) {
          syncBar.style.width = (cur + Math.random() * 12 + 6) + '%';
        }
      }, 600);

      try {
        const res = await apiFetch(API_BASE + '/api/sync-bb', { method: 'POST' });
        const data = await res.json();
        showToast(data.message || 'Синхронизация запущена в фоне');

        setTimeout(async () => {
          clearInterval(progTimer);
          if (syncBar) syncBar.style.width = '100%';

          await Promise.all([loadTasksData(), loadStatsData()]);
          renderFocusView();
          if (state.currentTab === 'tasks') renderTasksMainView();
          showToast('Данные обновлены!');

          setTimeout(() => {
            state.isSyncing = false;
            syncBtn.classList.remove('is-loading');
            if (syncText) syncText.textContent = 'Обновить данные';
            if (syncTrack) syncTrack.classList.remove('active');
            if (syncBar) syncBar.style.width = '0%';
          }, 450);
        }, 3200);
      } catch (e) {
        clearInterval(progTimer);
        showToast('Не удалось запустить синхронизацию');
        state.isSyncing = false;
        syncBtn.classList.remove('is-loading');
        if (syncText) syncText.textContent = 'Обновить данные';
        if (syncTrack) syncTrack.classList.remove('active');
        if (syncBar) syncBar.style.width = '0%';
      }
    });
  }
}

// -------------------------------------------------------------
// MOBILE UI: TASK DETAIL BOTTOM SHEET & KEYBOARD AVOIDANCE
// -------------------------------------------------------------
function setupTaskDetailSheet() {
  const overlay = document.getElementById('task-detail-overlay');
  const closeBtn = document.getElementById('task-detail-close-btn');

  if (!overlay) return;

  const closeSheet = () => {
    overlay.classList.remove('active');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeSheet);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeSheet();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('active')) {
      closeSheet();
    }
  });

  // Global event delegation for task items
  document.body.addEventListener('click', (e) => {
    // If clicked inside checkbox or file link, do not open detail sheet
    if (e.target.closest('.custom-checkbox') || e.target.closest('.task-checkbox-hit-area') || e.target.closest('.btn-file-link') || e.target.closest('.doc-open-btn') || e.target.closest('a')) {
      return;
    }

    const taskRow = e.target.closest('.task-row, .urgent-task-item');
    if (taskRow && taskRow.dataset.taskId) {
      const taskId = parseInt(taskRow.dataset.taskId, 10);
      if (!isNaN(taskId)) {
        openTaskDetailSheet(taskId);
      }
    }
  });
}

function openTaskDetailSheet(taskId) {
  const overlay = document.getElementById('task-detail-overlay');
  if (!overlay) return;

  const task = state.tasks.find((t) => t.id === taskId);
  if (!task) return;

  const subjEl = document.getElementById('task-detail-subject');
  const titleEl = document.getElementById('task-detail-title');
  const statusEl = document.getElementById('task-detail-status');
  const typeEl = document.getElementById('task-detail-type');
  const deadlineEl = document.getElementById('task-detail-deadline');
  const descEl = document.getElementById('task-detail-desc');
  const filesBox = document.getElementById('task-detail-files-box');
  const filesList = document.getElementById('task-detail-files-list');
  const toggleBtn = document.getElementById('task-detail-toggle-btn');
  const toggleText = document.getElementById('task-detail-toggle-text');
  const toggleIcon = document.getElementById('task-detail-toggle-icon');
  const aiBtn = document.getElementById('task-detail-ai-btn');
  const bbBtn = document.getElementById('task-detail-bb-btn');

  if (subjEl) subjEl.textContent = task.subject_name || 'Дисциплина';
  if (titleEl) titleEl.textContent = task.title;

  const isDone = task.status === 'done';
  if (statusEl) {
    statusEl.textContent = isDone ? 'Сдано' : 'К сдаче';
    statusEl.style.color = isDone ? 'var(--accent-green)' : 'var(--accent-orange)';
  }

  if (typeEl) {
    typeEl.textContent = task.task_type || 'Задание';
  }

  if (deadlineEl) {
    if (task.deadline) {
      deadlineEl.textContent = formatDeadlineDisplay(task.deadline);
    } else if (task.deadline_raw) {
      deadlineEl.textContent = task.deadline_raw;
    } else {
      deadlineEl.textContent = 'Срок не указан';
    }
  }

  if (descEl) {
    descEl.textContent = task.requirements || task.description || 'Требования уточняются у преподавателя на занятии.';
  }

  // Attachments
  const hasFiles = Boolean(task.file_url || (task.attachments && task.attachments.length > 0));
  if (filesBox && filesList) {
    if (hasFiles) {
      filesBox.style.display = 'block';
      if (task.attachments && task.attachments.length > 1) {
        filesList.innerHTML = task.attachments.map((att) => {
          const attId = att.id ? att.id : 'null';
          const attName = escapeHtml(att.name || 'Файл');
          return '<button type="button" class="btn-file-link download-btn glass-control" onclick="downloadTaskFile(' + task.id + ', ' + attId + ', \'' + attName + '\')" style="min-height: 44px; margin-bottom: 8px; width: 100%; justify-content: center;">' +
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
            '<span>Скачать: ' + attName + '</span>' +
          '</button>';
        }).join('');
      } else {
        const fileName = escapeHtml(task.file_name || 'файл');
        filesList.innerHTML = '<button type="button" class="btn-file-link download-btn glass-control" onclick="downloadTaskFile(' + task.id + ', null, \'' + fileName + '\')" style="min-height: 44px; width: 100%; justify-content: center;">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
          '<span>Скачать материалы (' + fileName + ')</span>' +
        '</button>';
      }
    } else {
      filesBox.style.display = 'block';
      const bbNotice = task.external_url || task.bb_course_url
        ? 'Методичка не прикреплена локально. Файлы и методические указания доступны в курсе Blackboard.'
        : 'Методические материалы не загружены в систему. Задание выполняется по указаниям преподавателя.';
      filesList.innerHTML = '<div class="sheet-files-empty">' +
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>' +
        '<span>' + escapeHtml(bbNotice) + '</span>' +
      '</div>';
    }
  }

  // Toggle Action Button
  if (toggleBtn) {
    toggleBtn.classList.toggle('is-completed', isDone);
    if (toggleText) toggleText.textContent = isDone ? 'Вернуть в работу' : 'Отметить сданным';
    if (toggleIcon) {
      toggleIcon.innerHTML = isDone
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><polyline points="20 6 9 17 4 12"/></svg>';
    }

    toggleBtn.onclick = async () => {
      toggleBtn.disabled = true;
      await handleTaskToggle(task.id);
      toggleBtn.disabled = false;
      const updated = state.tasks.find((t) => t.id === taskId);
      const nowDone = updated && updated.status === 'done';
      toggleBtn.classList.toggle('is-completed', nowDone);
      if (toggleText) toggleText.textContent = nowDone ? 'Вернуть в работу' : 'Отметить сданным';
      if (toggleIcon) {
        toggleIcon.innerHTML = nowDone
          ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>'
          : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><polyline points="20 6 9 17 4 12"/></svg>';
      }
      if (statusEl) {
        statusEl.textContent = nowDone ? 'Сдано' : 'К сдаче';
        statusEl.style.color = nowDone ? 'var(--accent-green)' : 'var(--accent-orange)';
      }
    };
  }

  // AI Summary button
  if (aiBtn) {
    aiBtn.onclick = () => {
      overlay.classList.remove('active');
      openLabSummaryModal(task.id);
    };
  }

  // Blackboard button
  const bbUrl = task.external_url || task.bb_course_url;
  if (bbBtn) {
    if (bbUrl) {
      bbBtn.style.display = 'inline-flex';
      bbBtn.href = bbUrl;
    } else {
      bbBtn.style.display = 'none';
    }
  }

  overlay.classList.add('active');
}

function setupKeyboardAvoidance() {
  let keyboardTimeout = null;

  document.addEventListener('focusin', (e) => {
    if (e.target && e.target.matches && e.target.matches('input, textarea, select')) {
      clearTimeout(keyboardTimeout);
      document.body.classList.add('keyboard-active');

      setTimeout(() => {
        try {
          e.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } catch (err) {
          // ignore
        }
      }, 120);
    }
  });

  document.addEventListener('focusout', (e) => {
    if (e.target && e.target.matches && e.target.matches('input, textarea, select')) {
      clearTimeout(keyboardTimeout);
      keyboardTimeout = setTimeout(() => {
        document.body.classList.remove('keyboard-active');
      }, 160);
    }
  });

  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
      const isKeyboard = window.visualViewport.height < window.innerHeight * 0.75;
      document.body.classList.toggle('keyboard-active', isKeyboard);
    });
  }
}