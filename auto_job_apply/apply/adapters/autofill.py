"""
Browser-based autofill adapter.

Strategy
--------
1. Open the URL in a headed Playwright browser (persistent profile so cookies survive).
2. Wait up to 30 s for any frame that contains form inputs to become visible.
3. Attempt to fill every recognised field using the caller-supplied values.
4. Upload the resume if a file input is found.
5. Take a screenshot, signal completion to the caller, then leave the browser open
   so the user can review the filled form and click Submit themselves.

The caller receives an AutofillResult once filling is done; the browser window stays
open in the background (daemon thread) until the user closes it.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Frame, sync_playwright


_ACTIVE_STOP_EVENTS: set[threading.Event] = set()
_ACTIVE_STOP_EVENTS_LOCK = threading.Lock()


def request_shutdown() -> None:
    """Signal all active autofill workers to stop and close their browser contexts."""
    with _ACTIVE_STOP_EVENTS_LOCK:
        events = list(_ACTIVE_STOP_EVENTS)
    for ev in events:
        ev.set()


@dataclass(frozen=True)
class AutofillResult:
    ok: bool
    filled_fields: int
    skipped_fields: list[str]          # fields that had no value or no matching input
    uploaded_resume: bool
    screenshot_path: str | None
    error: str | None = None


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
    """
    Open *url* in a browser, fill every field we have data for, and return.
    The browser stays open in a background thread so the user can review and submit.
    """
    browser_profile_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright as _check  # noqa: F401
    except ImportError:
        return AutofillResult(
            ok=False, filled_fields=0, skipped_fields=[],
            uploaded_resume=False, screenshot_path=None,
            error="Playwright is not installed. Run: pip install playwright",
        )

    fill_done = threading.Event()
    stop_requested = threading.Event()
    result_holder: list[AutofillResult] = []

    with _ACTIVE_STOP_EVENTS_LOCK:
        _ACTIVE_STOP_EVENTS.add(stop_requested)

    def _worker() -> None:
        with sync_playwright() as p:
            # --- launch browser ---
            try:
                context = p.chromium.launch_persistent_context(
                    str(browser_profile_dir),
                    headless=headless,
                )
            except Exception as exc:
                msg = str(exc)
                if "Executable doesn't exist" in msg or "playwright install" in msg.lower():
                    err = "Playwright browser not found. Run: python -m playwright install chromium"
                else:
                    err = f"Failed to launch browser: {exc}"
                result_holder.append(AutofillResult(
                    ok=False, filled_fields=0, skipped_fields=[],
                    uploaded_resume=False, screenshot_path=None, error=err,
                ))
                fill_done.set()
                return

            page = context.new_page()
            screenshot_path = screenshots_dir / "autofill.png"
            filled = 0
            skipped: list[str] = []
            uploaded_resume = False

            try:
                page.goto(url, wait_until="load", timeout=90_000)

                # Find the frame that contains the actual form inputs
                form_frame = _find_form_frame(page, timeout_ms=30_000)

                # Wait for inputs to become interactive
                try:
                    form_frame.locator("input").first.wait_for(state="visible", timeout=15_000)
                except PlaywrightTimeoutError:
                    pass

                # Debug snapshot before we touch anything
                try:
                    page.screenshot(
                        path=str(screenshots_dir / "autofill_before.png"),
                        full_page=True,
                    )
                except Exception:
                    pass

                # --- fill fields ---
                FIELD_SELECTORS = [
                    ("first_name", first_name, [
                        "input[name='first_name']",
                        "input[id='first_name']",
                        "input[autocomplete='given-name']",
                        "input[placeholder*='First' i]",
                    ]),
                    ("last_name", last_name, [
                        "input[name='last_name']",
                        "input[id='last_name']",
                        "input[autocomplete='family-name']",
                        "input[placeholder*='Last' i]",
                    ]),
                    ("email", email, [
                        "input[type='email']",
                        "input[name='email']",
                        "input[autocomplete='email']",
                    ]),
                    ("phone", phone, [
                        "input[type='tel']",
                        "input[name='phone']",
                        "input[name*='phone']",
                        "input[autocomplete='tel']",
                    ]),
                    ("linkedin", linkedin, [
                        "input[name='linkedin_url']",
                        "input[name*='linkedin']",
                        "input[id*='linkedin']",
                        "input[placeholder*='linkedin' i]",
                    ]),
                ]

                for field_name, value, selectors in FIELD_SELECTORS:
                    ok = _fill_field(form_frame, selectors, value)
                    if ok:
                        filled += 1
                    else:
                        skipped.append(
                            field_name if value else f"{field_name} (no value in profile)"
                        )

                # --- upload resume ---
                if resume_path:
                    uploaded_resume = _upload_resume(form_frame, resume_path)
                    if not uploaded_resume:
                        skipped.append("resume (file input not found)")
                else:
                    skipped.append("resume (no file in profile)")

                try:
                    page.screenshot(path=str(screenshot_path), full_page=True)
                except Exception:
                    pass

                result_holder.append(AutofillResult(
                    ok=True,
                    filled_fields=filled,
                    skipped_fields=skipped,
                    uploaded_resume=uploaded_resume,
                    screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
                ))

            except PlaywrightTimeoutError as exc:
                result_holder.append(AutofillResult(
                    ok=False, filled_fields=filled, skipped_fields=skipped,
                    uploaded_resume=uploaded_resume,
                    screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
                    error=f"Timed out loading or filling the page: {exc}",
                ))
            except Exception as exc:
                result_holder.append(AutofillResult(
                    ok=False, filled_fields=filled, skipped_fields=skipped,
                    uploaded_resume=uploaded_resume,
                    screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
                    error=f"Autofill failed: {exc}",
                ))
            finally:
                fill_done.set()

            # Keep the browser open so the user can review and submit manually.
            # Poll until the user closes the page/window.
            if not headless:
                try:
                    while not page.is_closed() and not stop_requested.is_set():
                        time.sleep(1)
                except Exception:
                    pass

            try:
                context.close()
            except Exception:
                pass

            with _ACTIVE_STOP_EVENTS_LOCK:
                _ACTIVE_STOP_EVENTS.discard(stop_requested)

    # Non-daemon so the thread (and browser) outlives Streamlit's request cycle
    t = threading.Thread(target=_worker, daemon=False, name="autofill-worker")
    t.start()
    fill_done.wait(timeout=120)

    if result_holder:
        return result_holder[0]

    with _ACTIVE_STOP_EVENTS_LOCK:
        _ACTIVE_STOP_EVENTS.discard(stop_requested)

    return AutofillResult(
        ok=False, filled_fields=0, skipped_fields=[],
        uploaded_resume=False, screenshot_path=None,
        error="Autofill did not complete within 120 s",
    )


def adapter_name() -> str:
    return "autofill"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_form_frame(page, timeout_ms: int = 30_000) -> Frame:
    """
    Poll all frames until one with visible form inputs is found.
    No ATS-specific heuristics - works for any job application page.
    """
    deadline = time.monotonic() + timeout_ms / 1000

    while time.monotonic() < deadline:
        frames = page.frames

        # Prefer a frame that already has a named first_name input
        for frame in frames:
            try:
                if frame.locator("input[name='first_name']").count() > 0:
                    return frame
            except Exception:
                pass

        # Fallback: any frame that has both an email input and a file input
        for frame in frames:
            try:
                has_email = frame.locator("input[type='email']").count() > 0
                has_file = frame.locator("input[type='file']").count() > 0
                if has_email and has_file:
                    return frame
            except Exception:
                pass

        # Fallback: any non-main frame that has at least 3 inputs
        for frame in frames:
            if frame == page.main_frame:
                continue
            try:
                if frame.locator("input").count() >= 3:
                    return frame
            except Exception:
                pass

        page.wait_for_timeout(500)

    # Last resort: main frame
    return page.main_frame


def _fill_field(frame: Frame, selectors: list[str], value: str | None) -> bool:
    """Try each selector in order; return True if any succeeded."""
    if not value:
        return False
    for selector in selectors:
        locator = frame.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=3_000)
            locator.scroll_into_view_if_needed(timeout=2_000)
            locator.fill(value, timeout=5_000)
            return True
        except Exception:
            continue
    return False


def _upload_resume(frame: Frame, resume_path: str) -> bool:
    file_path = Path(resume_path)
    if not file_path.exists():
        return False
    for selector in [
        "input[type='file'][name*='resume' i]",
        "input[type='file'][id*='resume' i]",
        "input[type='file'][accept*='pdf' i]",
        "input[type='file']",
    ]:
        locator = frame.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            locator.set_input_files(str(file_path), timeout=5_000)
            return True
        except Exception:
            continue
    return False
