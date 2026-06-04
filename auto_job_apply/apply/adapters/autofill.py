from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Frame, sync_playwright


@dataclass(frozen=True)
class AutofillResult:
    ok: bool
    filled_fields: int
    uploaded_resume: bool
    screenshot_path: str | None
    error: str | None = None


def supports_url(url: str) -> bool:
    lower = url.lower()
    host = urlparse(lower).netloc
    return (
        "grnhse" in host
        or "gh_jid=" in lower
        or "#grnhse_app" in lower
    )


def run_autofill(
    *,
    url: str,
    browser_profile_dir: Path,
    screenshots_dir: Path,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone: str | None,
    linkedin: str | None,
    resume_path: str | None,
    headless: bool = False,
) -> AutofillResult:
    browser_profile_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(browser_profile_dir),
            headless=headless,
        )
        page = context.new_page()

        screenshot_path = screenshots_dir / "autofill.png"
        filled_fields = 0
        uploaded_resume = False

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1500)

            form_frame = _pick_form_frame(page)

            filled_fields += _fill_first_match(
                form_frame,
                [
                    "input[name='first_name']",
                    "input[id='first_name']",
                    "input[name*='first_name']",
                ],
                first_name,
            )
            filled_fields += _fill_first_match(
                form_frame,
                [
                    "input[name='last_name']",
                    "input[id='last_name']",
                    "input[name*='last_name']",
                ],
                last_name,
            )
            filled_fields += _fill_first_match(
                form_frame,
                [
                    "input[name='email']",
                    "input[type='email']",
                    "input[name*='email']",
                ],
                email,
            )
            filled_fields += _fill_first_match(
                form_frame,
                [
                    "input[name='phone']",
                    "input[type='tel']",
                    "input[name*='phone']",
                ],
                phone,
            )
            filled_fields += _fill_first_match(
                form_frame,
                [
                    "input[name='linkedin_url']",
                    "input[name*='linkedin']",
                    "input[id*='linkedin']",
                ],
                linkedin,
            )

            if resume_path:
                uploaded_resume = _upload_resume(form_frame, resume_path)

            page.screenshot(path=str(screenshot_path), full_page=True)
            return AutofillResult(
                ok=True,
                filled_fields=filled_fields,
                uploaded_resume=uploaded_resume,
                screenshot_path=str(screenshot_path),
            )
        except PlaywrightTimeoutError as exc:
            return AutofillResult(
                ok=False,
                filled_fields=filled_fields,
                uploaded_resume=uploaded_resume,
                screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
                error=f"Timeout while loading or filling form: {exc}",
            )
        except Exception as exc:
            return AutofillResult(
                ok=False,
                filled_fields=filled_fields,
                uploaded_resume=uploaded_resume,
                screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
                error=f"Autofill failed: {exc}",
            )
        finally:
            context.close()


def adapter_name() -> str:
    return "autofill"


def _pick_form_frame(page) -> Frame:
    candidates = [page.main_frame, *page.frames]
    for frame in candidates:
        if frame.locator("input[name='first_name']").count() > 0:
            return frame
    for frame in candidates:
        if frame.locator("input[type='email']").count() > 0 and frame.locator("input[type='file']").count() > 0:
            return frame
    return page.main_frame


def _fill_first_match(frame: Frame, selectors: list[str], value: str | None) -> int:
    if not value:
        return 0
    for selector in selectors:
        locator = frame.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            locator.scroll_into_view_if_needed(timeout=2000)
            locator.fill(value, timeout=5000)
            return 1
        except Exception:
            continue
    return 0


def _upload_resume(frame: Frame, resume_path: str) -> bool:
    file_path = Path(resume_path)
    if not file_path.exists():
        return False

    for selector in [
        "input[type='file'][name*='resume']",
        "input[type='file'][id*='resume']",
        "input[type='file']",
    ]:
        locator = frame.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            locator.set_input_files(str(file_path), timeout=5000)
            return True
        except Exception:
            continue
    return False
