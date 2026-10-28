"""Headless-browser smoke test of the GitHub Pages site (docs/).

Opens every tab, makes a prediction, and fails on any console error or failed request.
Run after `python -m flight_delay.train`. Saves screenshots to reports/screenshots/.
"""
import functools
import http.server
import os
import threading

import pytest

from flight_delay.config import ROOT

playwright = pytest.importorskip("playwright.sync_api")
DOCS = ROOT / "docs"
SHOTS = ROOT / "reports" / "screenshots"


@pytest.fixture(scope="module")
def site():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()


@pytest.fixture(scope="module")
def page(site):
    with playwright.sync_playwright() as p:
        exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
        try:
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        except Exception as e:  # pragma: no cover
            pytest.skip(f"no chromium available: {e}")
        pg = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        # third-party fonts may be unreachable offline; everything else must load
        pg.on("requestfailed", lambda r: None if "fonts.g" in r.url else errors.append("failed: " + r.url))
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        pg.goto(site)
        pg.wait_for_selector("#board-rows tr")
        pg.errors = errors          # same list: keeps collecting through every test
        SHOTS.mkdir(parents=True, exist_ok=True)
        yield pg
        browser.close()


def settle(pg):
    """Let entrance animations and chart transitions finish before a screenshot."""
    pg.wait_for_timeout(900)


def _clean(errors):
    return [e for e in errors if "fonts.g" not in e and "net::ERR_FAILED" not in e]


def test_overview_board(page):
    assert page.locator("#board-rows tr").count() >= 7
    assert page.locator('[data-fill="auc"]').inner_text() == "0.765"
    settle(page)
    page.screenshot(path=str(SHOTS / "1-overview.png"), full_page=True)
    page.click("#board-next")
    assert page.locator("#board-rows tr").count() >= 7


def test_predictor_matches_model(page):
    page.click("#tab-predict")
    page.wait_for_selector("#t-prob:not(:empty)")
    shown = page.locator("#t-prob").inner_text()
    direct = page.evaluate("Math.round(App.model.predict(App.predictRecord()) * 100) + '%'")
    assert shown == direct
    before = shown
    page.check('#f-state input[value="3"]', force=True)
    assert page.locator("#t-prob").inner_text() != before, "airport state should change the risk"
    page.select_option("#f-origin", "LGA")
    page.wait_for_function("document.querySelector('#t-route').textContent.startsWith('LGA')")
    assert page.locator("#whatif li").count() >= 3
    page.select_option("#f-origin", "JFK")
    page.check('#f-state input[value="1"]', force=True)
    settle(page)
    page.screenshot(path=str(SHOTS / "2-predict.png"), full_page=True)


def test_explore_filters(page):
    page.click("#tab-explore")
    page.wait_for_selector("#x-summary strong")
    page.select_option("#x-origin", "EWR")
    assert "Newark" in page.locator("#x-summary").inner_text()
    page.select_option("#x-carrier", "UA")
    settle(page)
    page.screenshot(path=str(SHOTS / "3-explore.png"), full_page=True)
    page.select_option("#x-origin", "")
    page.select_option("#x-carrier", "")


def test_model_tab(page):
    page.click("#tab-model")
    page.wait_for_selector("#m-table tbody tr")
    assert page.locator("#m-table tbody tr").count() == 5
    assert "14,585" in page.locator("#cm").inner_text()
    settle(page)
    page.screenshot(path=str(SHOTS / "4-model.png"), full_page=True)


def test_replay_tab(page):
    page.click("#tab-replay")
    page.wait_for_selector("#r-rows tr")
    assert page.locator("#r-rows tr").count() == 20
    page.select_option("#r-outcome", "tp")
    assert all("Delay caught" in t for t in page.locator("#r-rows td.outcome").all_inner_texts())
    page.select_option("#r-outcome", "")
    settle(page)
    page.screenshot(path=str(SHOTS / "5-replay.png"), full_page=True)


def test_mobile_layout_and_no_errors(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(page.url.split("#")[0] + "#overview")
    page.wait_for_selector("#board-rows tr")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 390, f"horizontal scroll on mobile ({width}px)"
    settle(page)
    page.screenshot(path=str(SHOTS / "6-mobile.png"), full_page=True)
    assert _clean(page.errors) == [], page.errors
