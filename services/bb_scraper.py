"""
Blackboard Learn scraper module (bb.kai.ru) using Playwright.
Handles headless Chromium authentication, session persistence via storage_state,
recursive content folder crawling, strict item-level file isolation, exact deep linking,
and synchronization with the SQLite tasks database.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

import bs4
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from core.config import settings
from database.connection import async_session
from database.crud import (
    clear_bb_tasks,
    create_task,
    get_or_create_subject,
    get_task_by_title_and_subject,
)

logger = logging.getLogger("kai_assistant.bb_scraper")

DEFAULT_SESSION_PATH = Path("data/bb_session.json")


@dataclass
class ScrapedAttachment:
    name: str
    url: str


@dataclass
class ScrapedTask:
    title: str
    task_type: str
    details: Optional[str] = None
    deadline: Optional[datetime] = None
    attachments: List[ScrapedAttachment] = field(default_factory=list)
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    external_url: Optional[str] = None
    section_name: str = ""


@dataclass
class ScrapedCourse:
    title: str
    url: str
    course_id: Optional[str] = None
    tasks: List[ScrapedTask] = field(default_factory=list)


@dataclass
class ScrapeResult:
    is_authenticated: bool
    courses: List[ScrapedCourse] = field(default_factory=list)
    tasks_created: int = 0
    tasks_skipped: int = 0
    error: Optional[str] = None


def extract_course_id(url: str) -> Optional[str]:
    """Extract Blackboard course_id (e.g. '_10403_1') from URL parameters."""
    m = re.search(r"[?&](?:course_)?id=(_\d+_\d+)", url)
    return m.group(1) if m else None


def detect_task_type(title: str, section_name: str) -> str:
    """Infer student task type from title and parent section name."""
    combined = f"{title} {section_name}".lower()
    if "лаб" in combined or "л.р." in combined or "лр" in combined:
        return "лабораторная"
    if "доклад" in combined or "реферат" in combined:
        return "доклад"
    if "конспект" in combined:
        return "конспект"
    if "тест" in combined:
        return "тестирование"
    if "практик" in combined or "п.з." in combined:
        return "практическая"
    if "зачет" in combined or "экзамен" in combined:
        return "зачет"
    return "задание"


class BlackboardScraper:
    """Headless recursive scraper for Blackboard Learn (bb.kai.ru)."""

    def __init__(
        self,
        base_url: str = settings.bb_url,
        login: str = settings.bb_login,
        password: str = settings.bb_password,
        session_path: Path = DEFAULT_SESSION_PATH,
        headless: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.login = login
        self.password = password
        self.session_path = session_path
        self.headless = headless

    async def _handle_consent_dialog(self, page: Page) -> None:
        """Dismiss the cookie/consent overlay banner if present."""
        try:
            consent_btn = await page.query_selector(
                "#agree_button, .consent-button, button:has-text('Согласен'), "
                "button:has-text('Принять'), input[value*='Согласен']"
            )
            if consent_btn and await consent_btn.is_visible():
                await consent_btn.click(timeout=2000)
                logger.info("Dismissed Blackboard consent banner.")
        except Exception:
            pass

    async def _is_authenticated(self, page: Page) -> bool:
        """Check if user session is currently authenticated."""
        current_url = page.url.lower()
        if "login" in current_url:
            return False

        # Check for logout link, portal tabs, or user navigation
        logout_el = await page.query_selector("a[href*='logout'], #top_nav_bar, #global-nav-link, ul.portletList-img")
        return logout_el is not None

    async def authenticate(self, context: BrowserContext, page: Page) -> bool:
        """Perform login if session is expired or not present."""
        portal_url = f"{self.base_url}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1"

        # 1. If storage state exists, check if it is still valid
        if self.session_path.exists():
            logger.info("Existing session found at %s. Verifying...", self.session_path)
            try:
                await page.goto(portal_url, wait_until="domcontentloaded", timeout=20000)
                await self._handle_consent_dialog(page)
                if await self._is_authenticated(page):
                    logger.info("Authenticated successfully using saved session.")
                    return True
            except Exception as e:
                logger.warning("Saved session check failed (%s). Proceeding with fresh login.", e)

        # 2. Fresh login flow
        logger.info("Logging into Blackboard as %s...", self.login)
        login_url = f"{self.base_url}/webapps/login/"
        await page.goto(login_url, wait_until="domcontentloaded", timeout=25000)
        await self._handle_consent_dialog(page)

        # Wait for login inputs
        await page.wait_for_selector("input[name='user_id']", timeout=10000)
        await page.fill("input[name='user_id']", self.login)
        await page.fill("input[name='password']", self.password)

        login_btn = await page.query_selector("input#entry-login, input[type='submit']")
        if not login_btn:
            raise RuntimeError("Login submit button not found on Blackboard login page.")

        # Click submit with force=True to bypass any overlay banners
        await login_btn.click(force=True)
        await page.wait_for_load_state("domcontentloaded", timeout=25000)
        await asyncio.sleep(2)
        await self._handle_consent_dialog(page)

        # Verify authentication
        if not await self._is_authenticated(page):
            err_el = await page.query_selector("#loginErrorMessage, .receipt, .bad")
            err_text = (await err_el.inner_text()).strip() if err_el else "Unknown login error"
            raise RuntimeError(f"Blackboard login failed: {err_text}")

        # Save session to file
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(self.session_path))
        logger.info("Login successful. Session saved to %s", self.session_path)
        return True

    async def get_courses(self, page: Page) -> List[Tuple[str, str, Optional[str]]]:
        """Scrape active course links and IDs from the main Blackboard portal tab."""
        portal_url = f"{self.base_url}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1"
        if "tabaction" not in page.url.lower():
            await page.goto(portal_url, wait_until="domcontentloaded", timeout=20000)

        # Wait for the course portlet content to render
        try:
            await page.wait_for_selector(
                "ul.portletList-img a[href*='launcher?type=Course'], a[href*='launcher?type=Course']",
                timeout=12000
            )
        except Exception:
            pass

        await asyncio.sleep(2)
        course_links = await page.query_selector_all(
            "ul.portletList-img a[href*='launcher?type=Course'], a[href*='launcher?type=Course']"
        )

        courses = []
        seen_urls = set()

        for cl in course_links:
            name = (await cl.inner_text()).strip()
            href = (await cl.get_attribute("href") or "").strip()
            if not href or href.startswith("javascript:"):
                continue

            full_url = href if href.startswith("http") else f"{self.base_url}{href}"
            if full_url not in seen_urls and name:
                seen_urls.add(full_url)
                clean_name = re.sub(r"\s+", " ", name).strip()
                cid = extract_course_id(full_url)
                courses.append((clean_name, full_url, cid))

        logger.info("Found %d Blackboard courses for student.", len(courses))
        return courses

    async def _crawl_content_page(
        self,
        page: Page,
        course_id: Optional[str],
        url: str,
        depth: int = 0,
        max_depth: int = 3,
        parent_section: str = "",
        seen_urls: Optional[Set[str]] = None
    ) -> List[ScrapedTask]:
        """
        Recursively crawl Blackboard content items with strict file isolation per item
        and deep link generation.
        """
        if seen_urls is None:
            seen_urls = set()

        if depth > max_depth or url in seen_urls:
            return []
        seen_urls.add(url)

        logger.debug("Crawling depth=%d [%s]: %s", depth, parent_section, url)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning("Error loading content page %s: %s", url, e)
            return []

        html = await page.content()
        soup = bs4.BeautifulSoup(html, "html.parser")
        items = soup.select("ul.contentList > li, ul.contentListPlain > li")

        found_tasks: List[ScrapedTask] = []
        folders_to_crawl: List[Tuple[str, str]] = []

        for it in items:
            # =========================================================================
            # CRITICAL: STRICT VARIABLE ISOLATION PER ITEM
            # Never leak variables from previous iterations!
            # =========================================================================
            file_url: Optional[str] = None
            file_name: Optional[str] = None
            external_url: Optional[str] = None
            attachments: List[ScrapedAttachment] = []

            h3 = it.find("h3")
            if not h3:
                continue

            title = h3.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            h3_a = h3.find("a")
            h3_href = (h3_a.get("href") or "").strip() if h3_a else ""
            full_h3_url = (h3_href if h3_href.startswith("http") else f"{self.base_url}{h3_href}") if h3_href else ""

            # Content ID from li id (e.g. contentListItem:_486468_1) or href
            li_id = it.get("id") or ""
            content_id_match = re.search(r"_(\d+)_\d+", li_id)
            content_id = content_id_match.group(0) if content_id_match else None
            if not content_id and h3_href:
                c_m = re.search(r"content_id=(_\d+_\d+)", h3_href)
                if c_m:
                    content_id = c_m.group(1)

            # Detect item type: folder vs assignment
            img = it.find("img")
            img_src = (img.get("src") or "").lower() if img else ""
            img_alt = (img.get("alt") or "").lower() if img else ""
            is_folder = (
                "folder" in img_src
                or "folder" in img_alt
                or "папка" in img_alt
                or ("listcontent.jsp" in h3_href.lower() and "uploadassignment" not in h3_href.lower())
            )
            is_assignment = "uploadassignment" in h3_href.lower()

            # Extract attachments STRICTLY within this specific <li> container
            dav_links = it.select('a[href*="bbcswebdav"]')
            for da in dav_links:
                d_href = (da.get("href") or "").strip()
                if not d_href:
                    continue
                d_full = d_href if d_href.startswith("http") else f"{self.base_url}{d_href}"
                d_name = da.get_text(strip=True)
                if not d_name or d_name.startswith("xid-"):
                    d_name = Path(d_href.split("?")[0]).name
                attachments.append(ScrapedAttachment(name=d_name, url=d_full))

            # Strictly assign primary file only if attachments exist in THIS item
            if attachments:
                file_name = attachments[0].name
                file_url = attachments[0].url

            # Construct exact deep link
            if is_assignment:
                if content_id and course_id:
                    external_url = f"{self.base_url}/webapps/assignment/uploadAssignment?content_id={content_id}&course_id={course_id}&group_id=&mode=view"
                else:
                    external_url = full_h3_url
            elif is_folder and full_h3_url:
                external_url = full_h3_url
            elif full_h3_url and not full_h3_url.endswith("#"):
                external_url = full_h3_url
            elif content_id and course_id:
                external_url = f"{self.base_url}/webapps/blackboard/content/listContent.jsp?course_id={course_id}&content_id={content_id}"
            else:
                external_url = url

            # Details
            details_el = it.find(class_="details") or it.find(class_="vtbegenerated")
            details_text = details_el.get_text(separator="\n", strip=True) if details_el else ""

            # Composite details with file guidelines
            details_parts = []
            if details_text:
                details_parts.append(details_text[:800])
            if attachments:
                files_str = "\n".join([f"📎 {att.name}: {att.url}" for att in attachments])
                details_parts.append(f"Файлы методичек:\n{files_str}")
            final_details = "\n\n".join(details_parts) if details_parts else None

            task_type = detect_task_type(title, parent_section)

            # Determine whether this item is an actionable student task or reference document
            # (Skip pure empty container folders without files/assignments)
            is_actionable = (
                is_assignment
                or len(attachments) > 0
                or (not is_folder and (
                    task_type in ["лабораторная", "доклад", "конспект", "тестирование", "практическая", "зачет"]
                    or any(k in title.lower() for k in ["работа", "задание", "вопрос", "методич", "отчет", "фос", "лекци", "эссэ", "реферат"])
                ))
            )

            if is_actionable:
                found_tasks.append(
                    ScrapedTask(
                        title=title,
                        task_type=task_type,
                        details=final_details,
                        deadline=None,
                        attachments=attachments,
                        file_url=file_url,
                        file_name=file_name,
                        external_url=external_url,
                        section_name=parent_section
                    )
                )

            # Queue subfolder for recursive crawl
            if is_folder and full_h3_url and full_h3_url not in seen_urls:
                folders_to_crawl.append((full_h3_url, f"{parent_section} / {title}"))

        # Recurse into nested subfolders
        for f_url, f_section in folders_to_crawl:
            sub_tasks = await self._crawl_content_page(
                page=page,
                course_id=course_id,
                url=f_url,
                depth=depth + 1,
                max_depth=max_depth,
                parent_section=f_section,
                seen_urls=seen_urls
            )
            found_tasks.extend(sub_tasks)

        return found_tasks

    async def scrape_course(
        self,
        page: Page,
        course_title: str,
        course_url: str,
        course_id: Optional[str] = None
    ) -> ScrapedCourse:
        """Explore content areas recursively and parse assignment items for a single course."""
        logger.info("Scraping course: %s", course_title)
        course = ScrapedCourse(title=course_title, url=course_url, course_id=course_id)

        try:
            await page.goto(course_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(1.5)
        except Exception as e:
            logger.warning("Failed to open course %s: %s", course_title, e)
            return course

        if not course.course_id:
            course.course_id = extract_course_id(page.url) or extract_course_id(course_url)

        # 1. Identify content sections from left course menu
        menu_items = await page.query_selector_all("ul#courseMenuPalette_contents li a")
        sections_to_visit = []
        seen_sections = set()

        for mi in menu_items:
            s_name = (await mi.inner_text()).strip()
            s_href = (await mi.get_attribute("href") or "").strip()
            if not s_href or s_href.startswith("javascript:"):
                continue

            full_s_url = s_href if s_href.startswith("http") else f"{self.base_url}{s_href}"
            if not full_s_url.startswith(self.base_url):
                continue

            s_lower = s_name.lower()
            h_lower = s_href.lower()
            if any(skip in s_lower for skip in [
                "объявлен", "автор", "преподавател", "справка", "блог",
                "форум", "сообщен", "оценк", "журнал", "информация о курсе"
            ]):
                continue
            if "launchlink.jsp" in h_lower or "listlink.jsp" in h_lower:
                continue

            is_content_url = "listcontent.jsp" in h_lower
            has_keyword = any(
                kw in s_lower
                for kw in ["материал", "задан", "лабор", "практик", "семестр", "контент", "тест", "лекци", "модуль", "зачет", "курс"]
            )

            if (is_content_url or has_keyword) and full_s_url not in seen_sections:
                seen_sections.add(full_s_url)
                sections_to_visit.append((s_name, full_s_url))

        seen_urls: Set[str] = set()

        # 2. Check if landing page itself has content items
        landing_tasks = await self._crawl_content_page(
            page=page,
            course_id=course.course_id,
            url=page.url,
            depth=0,
            max_depth=3,
            parent_section="Главная курса",
            seen_urls=seen_urls
        )
        course.tasks.extend(landing_tasks)

        # 3. Visit each detected content section and crawl recursively
        for s_name, s_url in sections_to_visit:
            try:
                section_tasks = await self._crawl_content_page(
                    page=page,
                    course_id=course.course_id,
                    url=s_url,
                    depth=1,
                    max_depth=3,
                    parent_section=s_name,
                    seen_urls=seen_urls
                )
                course.tasks.extend(section_tasks)
            except Exception as e:
                logger.warning("Error scraping section '%s' in course '%s': %s", s_name, course_title, e)

        # 4. Deduplicate tasks within the course by title
        deduped: List[ScrapedTask] = []
        seen_titles = set()
        for t in course.tasks:
            if t.title not in seen_titles:
                seen_titles.add(t.title)
                deduped.append(t)

        course.tasks = deduped
        logger.info("Course '%s': parsed %d unique tasks/materials.", course_title, len(course.tasks))
        return course

    async def sync_with_db(
        self,
        courses: List[ScrapedCourse],
        clean_old: bool = True
    ) -> Tuple[int, int]:
        """
        Synchronize scraped courses and tasks with the SQLite database.
        Optionally clears old Blackboard tasks to eliminate obsolete/leaked entries.
        """
        created_count = 0
        skipped_count = 0

        async with async_session() as session:
            if clean_old:
                deleted_old = await clear_bb_tasks(session)
                logger.info("Cleared %d old Blackboard tasks for clean re-sync.", deleted_old)

            for c in courses:
                if not c.tasks:
                    continue

                # 1. Get or create subject
                subject = await get_or_create_subject(session, name=c.title)

                # 2. Save each task with isolated file and deep link
                for t in c.tasks:
                    if not clean_old:
                        existing = await get_task_by_title_and_subject(session, subject_id=subject.id, title=t.title)
                        if existing:
                            existing.file_url = t.file_url
                            existing.file_name = t.file_name
                            existing.external_url = t.external_url
                            existing.details = t.details
                            existing.task_type = t.task_type
                            await session.commit()
                            skipped_count += 1
                            continue

                    await create_task(
                        session=session,
                        subject_id=subject.id,
                        title=t.title,
                        task_type=t.task_type,
                        deadline=t.deadline,
                        status="todo",
                        source="bb",
                        details=t.details,
                        file_url=t.file_url,
                        file_name=t.file_name,
                        external_url=t.external_url
                    )
                    created_count += 1

        return created_count, skipped_count

    async def run_sync(self, clean_old: bool = True) -> ScrapeResult:
        """Execute full scraping and database synchronization pipeline."""
        if not self.login or not self.password:
            return ScrapeResult(
                is_authenticated=False,
                error="BB_LOGIN or BB_PASSWORD is not set in .env"
            )

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context_kwargs = {"ignore_https_errors": True}
            if self.session_path.exists():
                context_kwargs["storage_state"] = str(self.session_path)

            context: BrowserContext = await browser.new_context(**context_kwargs)
            page: Page = await context.new_page()

            try:
                is_auth = await self.authenticate(context, page)
                if not is_auth:
                    return ScrapeResult(is_authenticated=False, error="Authentication failed")

                courses_data = await self.get_courses(page)
                scraped_courses: List[ScrapedCourse] = []

                for c_title, c_url, c_id in courses_data:
                    c_obj = await self.scrape_course(page, c_title, c_url, course_id=c_id)
                    scraped_courses.append(c_obj)

                created, skipped = await self.sync_with_db(scraped_courses, clean_old=clean_old)

                return ScrapeResult(
                    is_authenticated=True,
                    courses=scraped_courses,
                    tasks_created=created,
                    tasks_skipped=skipped
                )

            except Exception as e:
                logger.exception("Blackboard scraping encountered an error: %s", e)
                return ScrapeResult(is_authenticated=False, error=str(e))
            finally:
                await context.close()
                await browser.close()
