/**
 * KAI Student OS 2.0 - Core Frontend Application
 * Linear & Bento-Grid Dashboard for Group 5108 (2nd subgroup)
 */

const API_BASE = '';

const state = {
  currentTab: 'focus',          // 'focus' | 'schedule' | 'tasks'
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
// App Initialization
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupSegmentControl();
  setupScheduleEvents();
  setupTasksEvents();
  setupTopBarEvents();
  setupSyncEvents();
  setupGeminiEvents();
  initAppData();
  setInterval(updateLiveLessonStatus, 30000);
});

async function initAppData() {
  updateCurrentDateDisplay();
  await Promise.all([
    loadTasksData(),
    loadScheduleData(),
    loadTodayScheduleForLive(),
    loadStatsData()
  ]);
  renderFocusView();
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

// -------------------------------------------------------------
// Top Bar & Navigation
// -------------------------------------------------------------
function updateCurrentDateDisplay() {
  const lbl = document.getElementById('focus-date-label');
  if (!lbl) return;
  const now = new Date();
  const options = { weekday: 'long', day: 'numeric', month: 'long' };
  const str = now.toLocaleDateString('ru-RU', options);
  lbl.textContent = str.charAt(0).toUpperCase() + str.slice(1);
}

function setupTopBarEvents() {
  const parityBtn = document.getElementById('parity-toggle-btn');
  if (parityBtn) {
    parityBtn.addEventListener('click', () => {
      state.scheduleParity = state.scheduleParity === 'чет' ? 'нечет' : 'чет';
      const parityLabel = document.getElementById('parity-label');
      if (parityLabel) parityLabel.textContent = state.scheduleParity.toUpperCase();
      const schedParityBadge = document.getElementById('schedule-parity-badge');
      if (schedParityBadge) schedParityBadge.textContent = state.scheduleParity.toUpperCase() + ' НЕДЕЛЯ';
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
  const navButtons = document.querySelectorAll('.bottom-nav .nav-btn');
  navButtons.forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tabName) {
  state.currentTab = tabName;
  document.querySelectorAll('.bottom-nav .nav-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });
  document.querySelectorAll('.app-view').forEach((view) => {
    view.classList.toggle('active', view.id === 'view-' + tabName);
  });
  if (tabName === 'focus') renderFocusView();
  else if (tabName === 'schedule') loadScheduleData();
  else if (tabName === 'tasks') renderTasksMainView();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// -------------------------------------------------------------
// TAB 1: ⚡ ФОКУС / СЕГОДНЯ (BENTO DASHBOARD)
// -------------------------------------------------------------
function renderFocusView() {
  updateCurrentDateDisplay();
  updateLiveLessonStatus();
  renderUrgentTasksBento();
  renderProgressRingBento();
}

async function loadTodayScheduleForLive() {
  const day = new Date().getDay();
  if (day === 0) {
    state.todaySchedule = [];
    updateLiveLessonStatus();
    return;
  }
  try {
    const res = await fetch(API_BASE + '/api/schedule?day=' + day + '&week=' + state.scheduleParity);
    if (res.ok) {
      const data = await res.json();
      state.todaySchedule = data.lessons || [];
      updateLiveLessonStatus();
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
    badge.className = 'status-pulse-badge live-done';
    statusText.textContent = '🌙 Выходной день';
    timeSlot.textContent = 'Отдых';
    title.textContent = 'Пар сегодня нет';
    bldgChip.className = 'hero-chip building-chip bldg-2';
    bldgChip.textContent = 'ИРЭФ-ЦТ';
    teacherText.textContent = 'Набирайся сил перед новой учебной неделей!';
    if (progressWrapper) progressWrapper.style.display = 'none';
    return;
  }

  if (!state.todaySchedule || state.todaySchedule.length === 0) {
    badge.className = 'status-pulse-badge live-done';
    statusText.textContent = '🌙 Свободный день';
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
      badge.className = 'status-pulse-badge live-active';
      statusText.textContent = '🟢 Сейчас идет пара';
      timeSlot.textContent = range.formatted;
      const typePrefix = lesson.discipl_type ? '[' + lesson.discipl_type + '] ' : '';
      title.textContent = typePrefix + lesson.discipl_name;
      const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
      bldgChip.className = 'hero-chip building-chip ' + chip.cls;
      bldgChip.textContent = chip.label;
      teacherText.textContent = lesson.prepod_name || 'Преподаватель не указан';

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
  for (const item of sorted) {
    const { lesson, range } = item;
    if (currentMin < range.startMin) {
      const waitMin = range.startMin - currentMin;
      badge.className = 'status-pulse-badge live-break';
      statusText.textContent = '🟡 До пары ' + waitMin + ' мин';
      timeSlot.textContent = 'Старт в ' + range.startStr;
      const typePrefix = lesson.discipl_type ? '[' + lesson.discipl_type + '] ' : '';
      title.textContent = typePrefix + lesson.discipl_name;
      const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
      bldgChip.className = 'hero-chip building-chip ' + chip.cls;
      bldgChip.textContent = chip.label;
      teacherText.textContent = lesson.prepod_name || 'Преподаватель не указан';

      if (progressWrapper) {
        progressWrapper.style.display = 'block';
        progressFill.style.width = '0%';
        timeLeftLabel.textContent = 'Перемена: ' + waitMin + ' мин';
        percentLabel.textContent = 'Скоро';
      }
      return;
    }
  }

  // 3. All lessons for today are completed
  badge.className = 'status-pulse-badge live-done';
  statusText.textContent = '🌙 Пары завершены';
  timeSlot.textContent = 'Свободен';
  title.textContent = 'Учебный день завершен!';
  bldgChip.className = 'hero-chip building-chip bldg-2';
  bldgChip.textContent = 'Отдых';
  teacherText.textContent = 'Все запланированные пары на сегодня прошли';
  if (progressWrapper) progressWrapper.style.display = 'none';
}

function renderUrgentTasksBento() {
  const container = document.getElementById('urgent-tasks-container');
  const allBtn = document.querySelector('.bento-urgent .tile-link-btn');
  if (!container) return;

  const actionable = state.tasks.filter((t) => !isReferenceMaterial(t));
  const pending = actionable.filter((t) => t.status === 'todo');

  if (allBtn) {
    allBtn.textContent = 'Все (' + pending.length + ')';
  }

  if (pending.length === 0) {
    container.innerHTML = '<div class="task-placeholder" style="color: var(--accent-mint); font-weight: 600;">🎉 Все задачи сданы! Долгов нет</div>';
    return;
  }

  const urgent = pending.slice(0, 3);
  container.innerHTML = urgent
    .map((task) => {
      return '<div class="urgent-task-item" id="urgent-item-' + task.id + '">' +
        '<div class="urgent-task-left">' +
          '<button class="custom-checkbox" data-task-id="' + task.id + '" title="Отметить как сданное">' +
            '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>' +
          '</button>' +
          '<div style="min-width:0; flex:1;">' +
            '<div class="urgent-task-title">' + escapeHtml(task.title) + '</div>' +
            '<div class="urgent-task-sub">' + escapeHtml(task.subject_name) + '</div>' +
          '</div>' +
        '</div>' +
        '<span class="urgent-badge">' + escapeHtml(task.task_type || 'Лаб') + '</span>' +
      '</div>';
    })
    .join('');

  container.querySelectorAll('.custom-checkbox').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tid = parseInt(btn.dataset.taskId, 10);
      handleTaskToggle(tid);
    });
  });
}

function renderProgressRingBento() {
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
    if (pct === 100) badge.textContent = 'Все сдано! 🚀';
    else if (pct >= 75) badge.textContent = 'Финишная прямая';
    else if (pct >= 50) badge.textContent = 'Больше половины!';
    else if (pct >= 25) badge.textContent = 'Хороший темп';
    else badge.textContent = 'В начале пути';
  }
}

// -------------------------------------------------------------
// TAB 2: 📅 ТАЙМЛАЙН РАСПИСАНИЯ
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
  if (parityBadge) parityBadge.textContent = state.scheduleParity.toUpperCase() + ' НЕДЕЛЯ';

  document.querySelectorAll('#schedule-day-pills .day-pill').forEach((pill) => {
    pill.classList.toggle('active', parseInt(pill.dataset.day, 10) === state.scheduleDay);
  });

  if (!container) return;
  container.innerHTML = '<div class="loader-skeleton"><div class="skeleton-line" style="width: 50%"></div><div class="skeleton-line" style="width: 80%"></div><div class="skeleton-line" style="width: 65%"></div></div>';

  try {
    const res = await fetch(API_BASE + '/api/schedule?day=' + state.scheduleDay + '&week=' + state.scheduleParity);
    if (!res.ok) throw new Error('Schedule API error');
    const data = await res.json();
    renderTimeline(data.lessons || []);
  } catch (err) {
    container.innerHTML = '<div class="task-placeholder" style="color: var(--accent-coral);">Ошибка загрузки расписания. Проверьте интернет.</div>';
  }
}

function renderTimeline(lessons) {
  const container = document.getElementById('timeline-list');
  if (!container) return;

  if (lessons.length === 0) {
    container.innerHTML = '<div class="task-placeholder" style="text-align: center; padding: 40px 16px;">' +
      '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" stroke-width="1.8" style="margin-bottom: 8px;">' +
        '<circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line>' +
      '</svg>' +
      '<div style="font-size: 1rem; font-weight: 700; color: var(--text-main);">В этот день занятий нет</div>' +
      '<div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Для 2-й подгруппы пары не запланированы</div>' +
    '</div>';
    return;
  }

  let html = '<div class="timeline-track"></div>';
  lessons.forEach((lesson) => {
    const timeInfo = getLessonTimeRange(lesson);
    const chip = getBuildingBadge(lesson.build_num, lesson.aud_num);
    const typeLower = (lesson.discipl_type || '').toLowerCase();
    let nodeClass = 'timeline-node';
    if (typeLower.includes('лаб')) nodeClass += ' node-lab';
    else if (typeLower.includes('пр')) nodeClass += ' node-prac';

    const homeworkBtn = lesson.todo_tasks_count > 0
      ? '<div class="timeline-homework-btn" data-discipl="' + escapeHtml(lesson.discipl_name) + '">' +
          '<span>⚡ К этой паре: ' + lesson.todo_tasks_count + ' заданий к сдаче</span>' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>' +
        '</div>'
      : '';

    html += '<div class="timeline-item">' +
      '<div class="timeline-node-wrapper"><div class="' + nodeClass + '"></div></div>' +
      '<div class="timeline-card">' +
        '<div class="timeline-card-top">' +
          '<span class="timeline-time-range">' + timeInfo.formatted + '</span>' +
          '<div class="timeline-chips-row">' +
            '<span class="building-badge ' + chip.cls + '">' + chip.label + '</span>' +
            (lesson.discipl_type ? '<span class="building-badge" style="background:var(--bg-card-high); color:var(--text-muted);">' + escapeHtml(lesson.discipl_type) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div class="timeline-title">' + escapeHtml(lesson.discipl_name) + '</div>' +
        '<div class="timeline-meta">' +
          '<div class="meta-row">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' +
            '<span>' + escapeHtml(lesson.prepod_name || 'Преподаватель не указан') + '</span>' +
          '</div>' +
        '</div>' +
        homeworkBtn +
      '</div>' +
    '</div>';
  });

  container.innerHTML = html;

  container.querySelectorAll('.timeline-homework-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      goToTasksForDiscipline(btn.dataset.discipl);
    });
  });
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
// TAB 3: 📝 ЗАДАНИЯ (SMART SPLIT)
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
  const chips = document.querySelectorAll('#tasks-status-row .filter-chip');
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
      fetch(API_BASE + '/api/tasks'),
      fetch(API_BASE + '/api/subjects')
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
    const res = await fetch(API_BASE + '/api/stats');
    if (res.ok) state.stats = await res.json();
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

  let html = '<button class="chip-subject ' + (state.tasksSubjectFilter === 0 ? 'active' : '') + '" data-subject-id="0">Все курсы (' + state.subjects.length + ')</button>';

  state.subjects.forEach((subj) => {
    const isActive = state.tasksSubjectFilter === subj.id;
    html += '<button class="chip-subject ' + (isActive ? 'active' : '') + '" data-subject-id="' + subj.id + '">' + escapeHtml(subj.name) + '</button>';
  });

  container.innerHTML = html;

  container.querySelectorAll('.chip-subject').forEach((chip) => {
    chip.addEventListener('click', () => {
      state.tasksSubjectFilter = parseInt(chip.dataset.subjectId, 10);
      container.querySelectorAll('.chip-subject').forEach((c) => c.classList.remove('active'));
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
    container.innerHTML = '<div class="task-placeholder" style="text-align: center; padding: 40px 16px;">' +
      '<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" stroke-width="1.8" style="margin-bottom: 8px;">' +
        '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>' +
      '</svg>' +
      '<div style="font-size: 1rem; font-weight: 700; color: var(--text-main);">Ничего не найдено</div>' +
      '<div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Попробуйте изменить параметры поиска или фильтра</div>' +
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

    html += '<div class="course-accordion-card">' +
      '<div class="course-header">' +
        '<div class="course-header-top">' +
          '<h4 class="course-name">' + escapeHtml(group.subject_name) + '</h4>' +
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

  container.querySelectorAll('.course-header').forEach((hdr) => {
    hdr.addEventListener('click', () => toggleAccordion(hdr));
  });

  container.querySelectorAll('.custom-checkbox').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tid = parseInt(btn.dataset.taskId, 10);
      handleTaskToggle(tid);
    });
  });
}

function renderActionableTaskRow(task) {
  const isDone = task.status === 'done';
  let actionsHtml = '';

  const geminiBtn = '<button class="btn-file-link btn-gemini-summary" data-task-id="' + task.id + '" title="✨ AI-разбор и шпаргалка">' +
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
      '<span>✨ Разбор лабы</span>' +
    '</button>';

  const bbUrl = task.external_url || task.bb_course_url;
  const bbCourseLink = bbUrl
    ? '<a href="' + bbUrl + '" target="_blank" rel="noopener noreferrer" class="btn-file-link bb-link-btn" title="Открыть задание в Blackboard">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>' +
        '<span>В BB</span>' +
      '</a>'
    : '';

  const hasFiles = Boolean(task.file_url || (task.attachments && task.attachments.length > 0));
  let fileBtns = '';

  if (hasFiles) {
    if (task.attachments && task.attachments.length > 1) {
      fileBtns = task.attachments
        .map((att) => {
          const dlUrl = att.download_url || (API_BASE + '/api/tasks/' + task.id + '/download');
          return '<a href="' + dlUrl + '" class="btn-file-link download-btn" download title="Прямое скачивание через бэкенд">' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
            '<span>Скачать: ' + escapeHtml(att.name || 'Файл') + '</span>' +
          '</a>';
        })
        .join('');
    } else {
      const fileName = task.file_name || (task.attachments && task.attachments[0] ? task.attachments[0].name : 'Файл');
      const dlUrl = API_BASE + '/api/tasks/' + task.id + '/download';
      fileBtns = '<a href="' + dlUrl + '" class="btn-file-link download-btn" download title="Прямое скачивание через бэкенд">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
        '<span>Скачать: ' + escapeHtml(fileName) + '</span>' +
      '</a>';
    }
  }

  actionsHtml = '<div class="task-actions-row">' + geminiBtn + fileBtns + bbCourseLink + '</div>';

  return '<div class="task-row ' + (isDone ? 'is-done' : '') + '" id="task-row-' + task.id + '">' +
    '<button class="custom-checkbox" data-task-id="' + task.id + '" title="Изменить статус">' +
      '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>' +
    '</button>' +
    '<div class="task-info">' +
      '<div class="task-title-text">' + escapeHtml(task.title) + '</div>' +
      '<div class="task-badges">' +
        '<span class="mini-badge mini-lab">' + escapeHtml(task.task_type || 'Лаб') + '</span>' +
        '<span class="mini-badge mini-course" title="' + escapeHtml(task.subject_name) + '">' + escapeHtml(task.subject_name) + '</span>' +
        (task.deadline ? '<span class="mini-badge" style="background:var(--accent-coral-bg); color:var(--accent-coral);">Срок: ' + escapeHtml(task.deadline) + '</span>' : '') +
      '</div>' +
      actionsHtml +
    '</div>' +
  '</div>';
}

function renderMaterialDocRow(task) {
  const hasFiles = Boolean(task.file_url || (task.attachments && task.attachments.length > 0));
  const dlUrl = API_BASE + '/api/tasks/' + task.id + '/download';
  const bbUrl = task.external_url || task.bb_course_url || 'https://bb.kai.ru';

  const geminiDocBtn = '<button class="doc-open-btn btn-gemini-summary" data-task-id="' + task.id + '" title="✨ Быстрый AI-разбор">' +
      '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
      '<span>✨ Разбор</span>' +
    '</button>';

  const downloadBtn = hasFiles
    ? '<a href="' + dlUrl + '" class="doc-open-btn doc-download-btn" download title="Скачать файл прямо на смартфон">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
        '<span>Скачать</span>' +
      '</a>'
    : '<span class="doc-open-btn" style="opacity:0.4; cursor:default; border:none; background:transparent;">Без файла</span>';

  const bbBtn = '<a href="' + bbUrl + '" target="_blank" rel="noopener noreferrer" class="doc-open-btn doc-bb-btn" title="Открыть в Blackboard">' +
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
        '<div class="doc-course-label">Курс: ' + escapeHtml(task.subject_name) + '</div>' +
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
  body.style.display = isHidden ? 'block' : 'none';
}

async function handleTaskToggle(taskId) {
  const task = state.tasks.find((t) => t.id === taskId);
  if (!task) return;

  const oldStatus = task.status;
  const newStatus = oldStatus === 'todo' ? 'done' : 'todo';
  task.status = newStatus;

  updateBadges();
  renderUrgentTasksBento();
  renderProgressRingBento();

  const taskRow = document.getElementById('task-row-' + taskId);
  if (taskRow) {
    taskRow.classList.toggle('is-done', newStatus === 'done');
  }

  showToast(
    newStatus === 'done'
      ? '✅ Работа отмечена как сданная!'
      : '↩️ Работа возвращена в долги'
  );

  try {
    const res = await fetch(API_BASE + '/api/tasks/' + taskId + '/toggle', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to toggle status');
    const updated = await res.json();
    task.status = updated.status;
  } catch (err) {
    task.status = oldStatus;
    updateBadges();
    renderUrgentTasksBento();
    renderProgressRingBento();
    if (taskRow) taskRow.classList.toggle('is-done', oldStatus === 'done');
    showToast('⚠️ Ошибка сохранения на сервере!');
  }
}

// -------------------------------------------------------------
// Blackboard Sync
// -------------------------------------------------------------
function setupSyncEvents() {
  const syncBtn = document.getElementById('bb-sync-btn');
  const syncText = document.getElementById('sync-btn-text');

  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      if (state.isSyncing) return;
      state.isSyncing = true;
      syncBtn.classList.add('is-loading');
      if (syncText) syncText.textContent = 'Синхронизация...';

      showToast('Запущен сбор заданий с bb.kai.ru...');

      try {
        const res = await fetch(API_BASE + '/api/sync-bb', { method: 'POST' });
        const data = await res.json();
        showToast(data.message || 'Синхронизация запущена в фоне');

        setTimeout(async () => {
          await Promise.all([loadTasksData(), loadStatsData()]);
          renderFocusView();
          if (state.currentTab === 'tasks') renderTasksMainView();
          showToast('Данные обновлены!');
          state.isSyncing = false;
          syncBtn.classList.remove('is-loading');
          if (syncText) syncText.textContent = 'Обновить из Blackboard';
        }, 5000);
      } catch (e) {
        showToast('⚠️ Не удалось запустить синхронизацию');
        state.isSyncing = false;
        syncBtn.classList.remove('is-loading');
        if (syncText) syncText.textContent = 'Обновить из Blackboard';
      }
    });
  }
}

// -------------------------------------------------------------
// Gemini AI Assistant & Voice Dictation
// -------------------------------------------------------------
function setupGeminiEvents() {
  const geminiOpenBtn = document.getElementById('gemini-open-btn');
  const geminiFabBtn = document.getElementById('gemini-fab-btn');
  const geminiCloseBtn = document.getElementById('gemini-close-btn');
  const geminiOverlay = document.getElementById('gemini-modal-overlay');
  const geminiText = document.getElementById('gemini-text-input');
  const geminiMicBtn = document.getElementById('gemini-mic-btn');
  const geminiMicStatus = document.getElementById('gemini-mic-status');
  const geminiSubmitBtn = document.getElementById('gemini-submit-btn');
  const geminiLoader = document.getElementById('gemini-shimmer-loader');
  const geminiResult = document.getElementById('gemini-result-card');

  function openGeminiSheet() {
    if (geminiOverlay) {
      geminiOverlay.classList.add('active');
      if (geminiText) {
        setTimeout(() => geminiText.focus(), 200);
      }
    }
  }

  function closeGeminiSheet() {
    if (geminiOverlay) {
      geminiOverlay.classList.remove('active');
    }
  }

  if (geminiOpenBtn) geminiOpenBtn.addEventListener('click', openGeminiSheet);
  if (geminiFabBtn) geminiFabBtn.addEventListener('click', openGeminiSheet);
  if (geminiCloseBtn) geminiCloseBtn.addEventListener('click', closeGeminiSheet);
  if (geminiOverlay) {
    geminiOverlay.addEventListener('click', (e) => {
      if (e.target === geminiOverlay) closeGeminiSheet();
    });
  }

  // Suggestion chips
  document.querySelectorAll('.gemini-suggest-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.dataset.prompt;
      if (geminiText && prompt) {
        geminiText.value = prompt;
        geminiText.focus();
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
        if (geminiMicStatus) geminiMicStatus.textContent = 'Слушаю...';
        showToast('🎙️ Говорите на русском языке...');
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (geminiText) {
          geminiText.value = geminiText.value ? geminiText.value + ' ' + transcript : transcript;
        }
        showToast('🎙️ Распознано: ' + transcript);
      };

      recognition.onerror = (e) => {
        console.warn('Speech recognition error:', e);
        showToast('Ошибка микрофона: ' + (e.error || 'неизвестно'));
      };

      recognition.onend = () => {
        isListening = false;
        geminiMicBtn.classList.remove('recording');
        if (geminiMicStatus) geminiMicStatus.textContent = 'Голос';
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
      showToast('Голосовой ввод не поддерживается данным браузером. Используйте клавиатуру.');
    });
  }

  // Parse task with Gemini
  if (geminiSubmitBtn) {
    geminiSubmitBtn.addEventListener('click', async () => {
      const text = geminiText ? geminiText.value.trim() : '';
      if (!text) {
        showToast('Пожалуйста, введите или надиктуйте текст задачи');
        return;
      }

      if (geminiLoader) geminiLoader.style.display = 'block';
      if (geminiResult) geminiResult.style.display = 'none';
      geminiSubmitBtn.disabled = true;

      try {
        const res = await fetch(API_BASE + '/api/ai/parse-task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Ошибка AI обработки');
        }

        const task = await res.json();

        // Render result box
        if (geminiResult) {
          let reqHtml = '';
          let reqText = '';
          if (task.requirements) {
            if (Array.isArray(task.requirements)) {
              reqText = task.requirements.join(', ');
            } else {
              reqText = String(task.requirements);
            }
          }
          if (reqText.trim()) {
            reqHtml = '<div style="margin-top: 8px; font-size: 0.8rem; color: var(--text-dim);">' +
              '<strong>Требования:</strong> ' + escapeHtml(reqText.trim()) +
            '</div>';
          }

          geminiResult.innerHTML = '<div class="gemini-success-header">' +
              '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>' +
              '<span>✨ Задача создана и сохранена в базу!</span>' +
            '</div>' +
            '<div class="gemini-success-body">' +
              '<div style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">' + escapeHtml(task.title) + '</div>' +
              '<div style="display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;">' +
                '<span class="gemini-success-tag">' + escapeHtml(task.subject_name) + '</span>' +
                '<span class="gemini-success-tag" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8;">' + escapeHtml(task.task_type || 'Задание') + '</span>' +
                (task.deadline ? '<span class="gemini-success-tag" style="background: rgba(248, 113, 113, 0.2); color: #f87171;">' + escapeHtml(task.deadline) + '</span>' : '') +
              '</div>' +
              reqHtml +
            '</div>';
          geminiResult.style.display = 'block';
        }

        if (geminiText) geminiText.value = '';
        showToast('✨ Задача успешно создана!');

        // Refresh state
        await Promise.all([loadTasksData(), loadStatsData()]);
        renderFocusView();
        if (state.currentTab === 'tasks') renderTasksMainView();

      } catch (err) {
        console.error('Gemini parse failed:', err);
        showToast('⚠️ Ошибка AI: ' + err.message);
      } finally {
        if (geminiLoader) geminiLoader.style.display = 'none';
        geminiSubmitBtn.disabled = false;
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

  // Delegation for all [ ✨ Разбор ] buttons
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

  // Show loading skeleton with animated shimmer
  labBody.innerHTML = '<div class="gemini-shimmer-card" style="margin: 0; padding: 18px;">' +
      '<div class="gemini-shimmer-header">' +
        '<svg class="gemini-spin-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">' +
          '<path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>' +
        '</svg>' +
        '<span>Gemini AI анализирует методические материалы и структуру работы...</span>' +
      '</div>' +
      '<div class="gemini-shimmer-bar" style="margin-top: 14px; height: 4px;"></div>' +
    '</div>';

  labOverlay.classList.add('active');

  try {
    const res = await fetch(API_BASE + '/api/ai/summarize-task/' + taskId, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Не удалось сгенерировать разбор');
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
          '<span>💡 Суть работы</span>' +
        '</div>' +
        '<p class="summary-section-text">' + escapeHtml(data.summary || 'Нет краткого описания') + '</p>' +
      '</div>' +
      '<div class="summary-section-box">' +
        '<div class="summary-section-title">' +
          '<span>🎒 Что взять с собой</span>' +
        '</div>' +
        '<ul class="summary-checklist">' + toBringItems + '</ul>' +
      '</div>' +
      '<div class="summary-section-box">' +
        '<div class="summary-section-title">' +
          '<span>📋 Порядок действий</span>' +
        '</div>' +
        '<ol class="summary-steps-list">' + stepsItems + '</ol>' +
      '</div>';
  } catch (err) {
    console.error('Failed to summarize lab:', err);
    labBody.innerHTML = '<div class="task-placeholder" style="color: var(--accent-coral); padding: 24px 0;">' +
        '⚠️ Ошибка: ' + escapeHtml(err.message) +
      '</div>';
  }
}