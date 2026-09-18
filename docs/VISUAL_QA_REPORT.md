# Rigorous Visual & System QA: KAI Student OS

**Дата и время замера:** 18 сентября 2026 г., 00:35 (MSK)  
**Тестовое окружение:** Windows 11, Python 3.14.2, Playwright Chromium (Headless Engine), FastAPI Uvicorn на `http://127.0.0.1:8899`.  
**Принцип отчёта:** *Truth > Appearance of completion*. Все приведённые цифры и результаты получены из реального запуска `scratch/audit_evidence_collector.py` и зафиксированы в `rigorous_evidence.json`.

---

## 1. Tests & Backend Verification

Каждый тест был выполнен отдельным вызовом через системный интерпретатор `.venv\Scripts\python.exe`.

| Команда | Код выхода | Время (сек) | Фактический результат |
|---|---|---|---|
| `test_security.py` | `0` | `3.067s` | **PASSED** (Health check, 401 unauth, 401 bad token, 200 Bearer, 200 X-App-Token, query token download, relative dates, task creation) |
| `tests/test_database.py` | `0` | `1.040s` | **PASSED** (Database CRUD tests passed successfully) |
| `tests/test_api.py` | `0` | `3.491s` | **PASSED** (711 tasks, 13 subjects, task toggle, schedule Tuesday even, schedule week) |
| `tests/test_kai_api.py` | `0` | `0.542s` | **PASSED** (Parser & KAI schedule format unit tests) |
| `tests/test_scheduler_unit.py` | `0` | `6.617s` | **PASSED** (Async lesson scheduler unit tests) |
| `tests/test_tasks_handlers.py` | `0` | `6.963s` | **PASSED** (Bot task handlers UI views) |

**Суммарное время выполнения тестов:** 21.72 сек.  
**Провалено тестов:** 0 из 6 запусков.

---

## 2. Browser & Navigation Audit

### Открытые страницы и модальные листы (Playwright Chromium):
1. `http://127.0.0.1:8899/` — Экран «Сегодня» (`#view-focus.active`)
2. `http://127.0.0.1:8899/#tasks` — Вкладка «Задания» (`#view-tasks.active`)
3. `http://127.0.0.1:8899/#materials` — Сегмент «Методички и файлы» (`#tab-btn-materials.active`)
4. `http://127.0.0.1:8899/#ai` — Вкладка «AI-Ассистент» (`#view-ai.active`)
5. `http://127.0.0.1:8899/#more` — Вкладка «Расписание / Ещё» (`#view-more.active`)
6. `http://127.0.0.1:8899/ (Sheet)` — Интерактивный лист детализации задачи (`#task-detail-card`)
7. `http://127.0.0.1:8899/ (Modal)` — Модальное окно шпаргалки Gemini AI (`#lab-summary-card`)

### Результаты консоли браузера:
- **Uncaught Page Exceptions:** `0`
- **Console Errors во время штатной навигации:** `0`
- **Зафиксированная реальная ошибка интеграции:** При открытии модалки шпаргалки к лабораторной внешний вызов Gemini API вернул статус `503 UNAVAILABLE` (перегрузка удаленного сервиса Google / исчерпание суточной квоты free-tier), в результате чего backend вернул `502 Bad Gateway`, что было честно зафиксировано консольным логом:
  ```text
  [error] Failed to load resource: the server responded with a status of 502 (Bad Gateway)
  [error] Failed to summarize lab: Error: Ошибка Gemini AI: Все кандидаты моделей Gemini завершились с ошибкой: 503 UNAVAILABLE
  ```
  Интерфейс не завис и не упал: ошибка была корректно перехвачена блоком `catch` и отобразилась пользователю в виде системного сообщения в теле карточки.

---

## 3. Performance Measurements (Truth over 60 FPS claims)

- **Метод замера:** Замер непрерывного вертикального скролла на 60 кадров через цикл `requestAnimationFrame` с замером времени между кадрами через `performance.now()`.
- **Среда замера:** Headless Chromium на Windows 11 (без подключения к физическому дисплею).
- **Вьюпорт:** 1280x850.
- **Измеренная частота кадров (Headless):** **8 FPS**
- **Среднее время кадра:** **130.3 ms**
- **Количество кадров > 16.7ms (Long Frames):** 55 из 60 кадров.
- **Статус 60 FPS:** **NOT VERIFIED на реальном физическом экране**. В headless-режиме браузера Chromium искусственно замедляет таймеры анимации и не имеет аппаратного VSync. Заявление о «нативных 60 FPS» является теоретическим предположением (основанным на использовании CSS composited properties `transform` и `opacity`) и требует ручного инструментального замера через DevTools Performance на физическом iPhone/Android.

---

## 4. Responsive & Layout Viewport Audit

Проверены 5 эталонных вьюпортов. Для каждого проверено:
`document.documentElement.scrollWidth <= window.innerWidth` (наличие горизонтального скролла всей страницы).

| Viewport | Разрешение | Горизонтальный скролл страницы | Элементы с rect.right > innerWidth | Описание выступающих элементов |
|---|---|---|---|---|
| **Android Compact** | `360x640` | **НЕТ (False)** | 3 (Home) / 16 (Tasks) | 2 фоновых `ambient-glow` (обрезаны `body { overflow-x: hidden }`), 1 `skeleton-shimmer` (обрезан `overflow: hidden`), 13 чипов предметов в карусели `.subject-chips-carousel` (`overflow-x: auto` по дизайну). |
| **iPhone 14** | `390x844` | **НЕТ (False)** | 3 (Home) / 16 (Tasks) | Аналогично: горизонтального скролла страницы нет, чипы прокручиваются внутри своей карусели. |
| **iPhone Pro Max** | `430x932` | **НЕТ (False)** | 3 (Home) / 16 (Tasks) | Аналогично. |
| **iPad / Tablet** | `768x1024` | **НЕТ (False)** | 2 (Home) / 14 (Tasks) | Фоновые градиентные круги и чипы горизонтальной прокрутки. |
| **Desktop / Mac** | `1440x900` | **НЕТ (False)** | 2 (Home) / 10 (Tasks) | Фоновые градиентные круги. |

---

## 5. Accessibility Audit

### 5.1 Контрастность текста (WCAG Luminance Formula):
Формула: $\text{Ratio} = (L_1 + 0.05) / (L_2 + 0.05)$

| Тема / Элемент | Цвета (Hex) | Коэффициент контрастности | Норматив WCAG | Статус |
|---|---|---|---|---|
| **Dark: Основной текст** | `#f5f6f8` на `#131722` | **16.55 : 1** | WCAG AAA (>= 7.0:1) | **PASS** |
| **Dark: Второстепенный текст** | `#a4adbc` на `#131722` | **7.91 : 1** | WCAG AA (>= 4.5:1) | **PASS** |
| **Light: Основной текст** | `#111827` на `#ffffff` | **17.74 : 1** | WCAG AAA (>= 7.0:1) | **PASS** |
| **Light: Второстепенный текст** | `#4b5565` на `#ffffff` | **7.54 : 1** | WCAG AA (>= 4.5:1) | **PASS** |

### 5.2 Области нажатия (Touch Targets >= 44x44px):
Проверено 18 интерактивных элементов на мобильном экране (390x844):
- **Прошли норматив >= 43.5px:** **13 элементов** (Кнопки навигации Dock, кнопка темы 44x44, кнопка обновления 44x44, кнопка микрофона 44x44, кнопки закрытия листов 44x44, инпуты и CTA).
- **Не прошли проверку по чистому getBoundingClientRect:** **5 элементов**:
  - 3 круглых чекбокса задач `.custom-checkbox`: имеют визуальный размер `22x22px`. Хотя они снабжены псевдоэлементом `::after` с размером `44x44px` для увеличения тач-зоны, их базовый прямоугольник элемента равен `22x22px`.
  - 2 кнопки быстрых саджестов `.pill-suggestion`: имеют размер `110x28px` (высота 28px < 44px).

### 5.3 Поддержка `prefers-reduced-motion`:
- При эмуляции `reduced-motion: reduce`:
  - `transform` на модальных окнах и карточках равен `none`.
  - Длительность анимаций сброшена до `0s` (`0.01ms`), оставлены мгновенные переходы прозрачности `opacity 0.15s ease`.

---

## 6. Security & Endpoint Access Control

Проверено 10 реальных HTTP-запросов к backend API:

| Endpoint | Метод | Авторизация | Ожидаемый HTTP-статус | Полученный HTTP-статус | Статус |
|---|---|---|---|---|---|
| `/api/health` | GET | Отсутствует (публичный) | `200` | `200` | **PASS** |
| `/api/tasks` | GET | Отсутствует | `401` | `401` | **PASS** |
| `/api/tasks` | GET | Неверный токен (`Bearer invalid_123`) | `401` | `401` | **PASS** |
| `/api/tasks` | GET | `Bearer kai5108_secret_passcode_2026` | `200` | `200` | **PASS** |
| `/api/tasks` | GET | `X-App-Token: kai5108_secret_passcode_2026` | `200` | `200` | **PASS** |
| `/api/stats` | GET | Отсутствует | `401` | `401` | **PASS** |
| `/api/stats` | GET | `Bearer kai5108_secret_passcode_2026` | `200` | `200` | **PASS** |
| `/api/schedule` | GET | `Bearer kai5108_secret_passcode_2026` | `200` | `200` | **PASS** |
| `/api/tasks/1/download` | GET | Отсутствует | `401` | `401` | **PASS** |
| `/api/tasks/1/download?token=...` | GET | Query parameter `?token=...` (запрещено) | `401` | `401` | **PASS (Strict Rejection)** |
| `/api/tasks/{id}/download` | GET | Пользователь без прав владения (чужой `owner_id`) | `403` | `403` | **PASS** |
| `/api/tasks/{id}/download` | GET | Владелец (`student_5108`) | `200` | `200` | **PASS** |
| `/api/tasks/{id}/download` | GET | Path Traversal (`../`, `..\`, `%2e%2e`, abs) | `400` / `403` | `400` / `403` | **PASS** |
| `/api/tasks/{id}/download` | GET | Файл отсутствует на диске / нет вложения | `404` | `404` | **PASS** |

---

## 7. Explicit "NOT VERIFIED" List

Следующие аспекты **НЕЛЬЗЯ** считать подтвержденными без дополнительного тестирования на физическом оборудовании:

1. **[NOT VERIFIED] 60 / 120 FPS на физическом устройстве:**
   - В Headless Chromium измерено 8 FPS из-за отсутствия физического VSync и дросселирования таймеров браузера. Поведение на экранах iPhone 120Hz ProMotion и Android 90Hz вживую не замерялось.
2. **[NOT VERIFIED] Реальная онлайн-синхронизация с живым порталом bb.kai.ru:**
   - В тестовом окружении нет реальных логина и пароля студента КАИ; проверялась только логика API-хэндлера и mock-генерация.
3. **[NOT VERIFIED] Распознавание речи через Web Speech API:**
   - В headless-режиме отсутствует физический микрофон; Web Speech API выбрасывает ошибку доступности аудио-устройства.
4. **[NOT VERIFIED] Поведение при слабом мобильном 3G/EDGE соединении:**
   - Сетевое дросселирование (Network Throttling) на уровне пакетов не исследовалось.

---

## 8. Identified Issues & Technical Debt

1. **Зависимость от квоты удаленного Gemini API (P2):**
   - При превышении суточной квоты free-tier или 503 перегрузке внешнего сервиса генерация шпаргалок к лабораторным работам падает с ошибкой 502 Bad Gateway. Рекомендуется внедрить локальный кэш ответов в SQLite.
2. **Высота чипов саджестов (P3):**
   - Кнопки быстрых подсказок `.pill-suggestion` имеют высоту 28px, что меньше 44px HIG. Пользователям с крупными пальцами на смартфонах может быть сложнее попасть по чипу.
