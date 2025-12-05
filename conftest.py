# conftest.py
"""
Conftest hoàn chỉnh cho dự án Bookworms Store
- Screenshot cho PASS/FAIL
- Metadata từ marker/docstring/log_step
- Parse Test Data -> TD_<key>
- Auto-detect View & Category (Performance/Functional) và UI vs UX detection (heuristics)
- Ghi kết quả vào test_results_master.xlsx
"""
import os
import re
import time
import shutil
import json
import inspect
from datetime import datetime

import pandas as pd
import pytest

MASTER_FILE = os.path.join(os.getcwd(), "test_results_master.xlsx")
TEMP_FILE = os.path.join(os.getcwd(), "test_results_temp.xlsx")

_test_results = []
_test_steps = {}          # { pretty_id: [steps...] }
_test_screenshots = {}    # { pretty_id: screenshot_path }
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
_driver_instance = None


# --------------------------
# pytest options
# --------------------------
def pytest_addoption(parser):
    parser.addoption("--browser", default="chrome")
    parser.addoption("--env", default="local")
    parser.addoption("--perf-threshold", type=float, default=2.0,
                     help="Threshold in seconds to classify a long-running test as Performance test")


# --------------------------
# VIEW_MAP (dựa trên router PHP bạn cung cấp)
# --------------------------
VIEW_MAP = {
    "/": "Home",
    "/home": "Home",
    "/about": "About",
    "/search": "Search Results",
    "/product_all": "Product List",
    "/product": "Product By Type",
    "/detail": "Product Detail",
    "/cart": "Cart",
    "/addCart": "Cart Action",
    "/del": "Cart Action",
    "/delCart": "Cart Action",
    "/pay": "Checkout",
    "/payHistory": "Payment History",
    "/detailBill": "Bill Detail",
    "/cancleBill": "Bill Action",
    "/recieved": "Bill Action",
    "/received": "Bill Action",
    "/manageProduct": "Manage Products",
    "/manage": "Manage Product Detail",
    "/create": "Create Product",
    "/manageBill": "Manage Bills",
    "/manageDetailBill": "Manage Bill Detail",
    "/users": "Manage Users",
    "/userInfo": "User Info",
    "/passChange": "User Password Change",
    "/manage/product": "Manage Products",
    "/manage/create": "Manage Create Product",
    "/manage/product/": "Manage Product Detail",
    "/manage/bills": "Manage Bills",
    "/manage/bill": "Manage Bill Detail",
}


# --------------------------
# Utility: pretty nodeid
# --------------------------
def generate_pretty_nodeid(item):
    try:
        fpath = getattr(item, "fspath", None)
        if fpath:
            file = os.path.basename(fpath)
        else:
            file = os.path.basename(item.nodeid.split("::", 1)[0])
    except Exception:
        file = "unknown"
    try:
        funcname = getattr(item, "name", None) or item.nodeid.split("::")[-1]
    except Exception:
        funcname = "test_unknown"
    file_prefix = "".join([w[0].upper() for w in file.replace(".py", "").split("_") if w])
    slug = re.sub(r"^test_", "", funcname)
    numeric = abs(hash(slug)) % 1000
    return f"{file_prefix}-T{numeric:03d}"


# --------------------------
# Fixture: log_step
# --------------------------
@pytest.fixture
def log_step(request):
    """
    Sử dụng trong test: log_step("Test Data: keyword=abc; qty=1")
    """
    pretty_id = generate_pretty_nodeid(request.node)
    _test_steps.setdefault(pretty_id, [])
    def _log(step_text):
        _test_steps[pretty_id].append(step_text)
    return _log


# --------------------------
# Screenshot helper
# --------------------------
def try_capture_screenshot_for_pretty_id(pretty_id, driver_obj=None):
    global _driver_instance
    screenshot_path = ""
    try:
        if not driver_obj:
            driver_obj = globals().get("_driver_instance", None)
        if not driver_obj:
            print(f"[DEBUG] No driver available to take screenshot for {pretty_id}")
            return ""
        try:
            sid = getattr(driver_obj, "session_id", None)
            print(f"[DEBUG] Taking screenshot for {pretty_id}, session_id={sid}")
        except Exception:
            pass
        sc_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(sc_dir, exist_ok=True)
        sc_file = f"{pretty_id}_{RUN_ID}.png"
        screenshot_path = os.path.join(sc_dir, sc_file)
        try:
            ok = driver_obj.save_screenshot(screenshot_path)
            print(f"[DEBUG] save_screenshot returned: {ok} -> {screenshot_path}")
        except Exception as e:
            print(f"[DEBUG] save_screenshot raised: {e}, trying fallback get_screenshot_as_file")
            try:
                driver_obj.get_screenshot_as_file(screenshot_path)
                print(f"[DEBUG] get_screenshot_as_file succeeded -> {screenshot_path}")
            except Exception as e2:
                print(f"[DEBUG] get_screenshot_as_file also failed: {e2}")
                screenshot_path = ""
        if screenshot_path and os.path.exists(screenshot_path):
            return screenshot_path
        else:
            print(f"[DEBUG] Screenshot file not found after attempts: {screenshot_path}")
            return ""
    except Exception as e:
        print(f"[DEBUG] Unexpected error when capturing screenshot: {e}")
        return ""


# --------------------------
# Driver fixture
# --------------------------
@pytest.fixture
def driver(request):
    global _driver_instance
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        raise RuntimeError(f"Cannot import selenium/webdriver_manager: {e}")

    driver_inst = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    _driver_instance = driver_inst
    try:
        request.node._driver = driver_inst
    except Exception:
        pass
    pretty_id = generate_pretty_nodeid(request.node)
    yield driver_inst
    try:
        if pretty_id not in _test_screenshots:
            p = try_capture_screenshot_for_pretty_id(pretty_id, driver_inst)
            if p:
                _test_screenshots[pretty_id] = p
    except Exception as e:
        print(f"[DEBUG] Error during driver teardown screenshot: {e}")
    try:
        driver_inst.quit()
    except Exception:
        pass
    _driver_instance = None


# --------------------------
# Metadata extraction & TestData parsing
# --------------------------
def extract_metadata_for_item(item, pretty_id):
    meta = {
        "title": "",
        "description": "",
        "precondition": "",
        "testdata_raw": "",
        "testdata_kv": {},
        "priority": "",
        "view": ""
    }
    try:
        for m in item.iter_markers():
            if m.name == "tc":
                for k, v in m.kwargs.items():
                    k_lower = k.lower()
                    if k_lower in ("title", "desc", "description"):
                        meta["title"] = v
                    elif k_lower in ("pre", "precondition"):
                        meta["precondition"] = v
                    elif k_lower in ("data", "testdata", "test_data"):
                        meta["testdata_raw"] = v
                    elif k_lower == "priority":
                        meta["priority"] = v
                    elif k_lower == "view":
                        meta["view"] = v
                return meta
    except Exception:
        pass
    try:
        doc = inspect.getdoc(getattr(item, "obj", None)) or ""
        if doc:
            for line in doc.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k.startswith("title"):
                    meta["title"] = v
                elif k.startswith("description") or k.startswith("desc"):
                    meta["description"] = v
                elif k.startswith("precondition") or k.startswith("pre"):
                    meta["precondition"] = v
                elif k.startswith("testdata") or k.startswith("test data") or k.startswith("data"):
                    meta["testdata_raw"] = v
                elif k.startswith("priority"):
                    meta["priority"] = v
                elif k.startswith("view"):
                    meta["view"] = v
    except Exception:
        pass
    try:
        steps = _test_steps.get(pretty_id, [])
        for s in steps:
            if isinstance(s, str):
                low = s.lower()
                if low.startswith("test data:") or low.startswith("testdata:"):
                    meta["testdata_raw"] = s.split(":",1)[1].strip()
                if low.startswith("view:"):
                    meta["view"] = s.split(":",1)[1].strip()
    except Exception:
        pass
    raw = meta.get("testdata_raw", "") or ""
    kv = {}
    if raw:
        raw_strip = raw.strip()
        if raw_strip.startswith("{") and raw_strip.endswith("}"):
            try:
                parsed = json.loads(raw_strip)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        safe_key = re.sub(r"\s+", "_", str(k).lower())
                        kv[safe_key] = str(v)
            except Exception:
                pass
        if not kv:
            parts = re.split(r"[;|,]\s*", raw)
            for p in parts:
                if "=" in p:
                    k, v = p.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k:
                        safe_key = re.sub(r"\s+", "_", k.lower())
                        kv[safe_key] = v
                else:
                    if p.strip():
                        kv.setdefault("value", p.strip())
    meta["testdata_kv"] = kv
    return meta


# --------------------------
# View detection helpers
# --------------------------
def _match_view_from_url(url, view_map=None):
    if not url:
        return ""
    vm = view_map or VIEW_MAP
    for pattern, name in vm.items():
        try:
            if pattern in url:
                return name
        except Exception:
            continue
    try:
        path = url.split("://")[-1].split("/",1)[-1].split("?")[0]
        parts = [p for p in path.split("/") if p]
        if parts:
            return parts[0] if len(parts) == 1 else parts[-1]
    except Exception:
        pass
    return ""


def auto_detect_type_and_view(item, pretty_id, duration_s, driver_obj=None, meta=None, config=None):
    result = {"category": "Functional", "view": "", "page_url": "", "page_title": ""}
    perf_threshold = 2.0
    try:
        if config:
            perf_threshold = float(config.getoption("--perf-threshold"))
    except Exception:
        pass
    try:
        if meta:
            if meta.get("view"):
                result["view"] = meta.get("view")
    except Exception:
        pass
    try:
        name = getattr(item, "name", "") or item.nodeid
        name_l = (name or "").lower()
        doc = inspect.getdoc(getattr(item, "obj", None)) or ""
        doc_l = (doc or "").lower()
        if any(k in name_l for k in ("perf", "performance", "load", "stress", "benchmark")) or \
           any(k in doc_l for k in ("performance", "load test", "stress test", "benchmark")):
            result["category"] = "Performance"
    except Exception:
        pass
    if driver_obj:
        if result["category"] == "Functional":
            result["category"] = "UI"  # temporarily mark UI if driver present; will refine later with UI/UX detector
        try:
            cur = getattr(driver_obj, "current_url", None) or ""
            title = getattr(driver_obj, "title", "") or ""
            result["page_url"] = cur
            result["page_title"] = title
            if not result["view"]:
                matched = _match_view_from_url(cur)
                if matched:
                    result["view"] = matched
        except Exception:
            pass
    try:
        steps = _test_steps.get(pretty_id, [])
        for s in steps:
            if isinstance(s, str):
                sl = s.lower()
                if sl.startswith("view:"):
                    result["view"] = s.split(":",1)[1].strip()
    except Exception:
        pass
    try:
        if duration_s is not None and float(duration_s) >= float(perf_threshold):
            if result["category"] not in ("UI", "Performance"):
                result["category"] = "Performance"
    except Exception:
        pass
    return result


# --------------------------
# Detect UI vs UX (heuristics)
# --------------------------
def detect_ui_or_ux(item, pretty_id, driver_obj=None, meta=None, test_steps=None, test_case_desc=""):
    ui_score = 0
    ux_score = 0
    doc = ""
    src_l = ""
    try:
        for m in item.iter_markers():
            if m.name == "tc" and m.kwargs:
                t = m.kwargs.get("type") or m.kwargs.get("test_type") or m.kwargs.get("kind")
                if t:
                    t_l = str(t).lower()
                    if "ui" in t_l and "ux" not in t_l:
                        return "UI"
                    if "ux" in t_l and "ui" not in t_l:
                        return "UX"
    except Exception:
        pass
    try:
        doc = inspect.getdoc(getattr(item, "obj", None)) or ""
        for line in doc.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip().lower() == "type":
                    val = v.strip().lower()
                    if "ui" in val and "ux" not in val:
                        return "UI"
                    if "ux" in val and "ui" not in val:
                        return "UX"
    except Exception:
        pass
    try:
        name = getattr(item, "name", "") or item.nodeid
        name_l = (name or "").lower()
        doc_l = (doc or "").lower()
        ui_keys = ["ui", "visual", "layout", "pixel", "css", "color", "font", "responsive", "visual-regression"]
        ux_keys = ["ux", "flow", "journey", "usability", "accessibility", "a11y", "task", "scenario"]
        for k in ui_keys:
            if k in name_l or k in doc_l:
                ui_score += 2
        for k in ux_keys:
            if k in name_l or k in doc_l:
                ux_score += 2
    except Exception:
        pass
    try:
        src = inspect.getsource(getattr(item, "obj", item))
        src_l = src.lower()
        ui_patterns = [
            ".value_of_css_property(", ".size", ".location", ".rect", ".screenshot(", "pixel", "imagehash",
            "get_css", "get_attribute('style')", "get_attribute(\"style\")", "style."
        ]
        ux_patterns = ["assert 'success' in", "assert 'error' in", "current_url", "title", "click()", "send_keys(", "wait.until", "axe.run", "accessibility", "a11y"]
        for p in ui_patterns:
            if p in src_l:
                ui_score += 2
        for p in ux_patterns:
            if p in src_l:
                ux_score += 1
        if "axe.run" in src_l or "accessibility" in src_l or "a11y" in src_l:
            ux_score += 3
    except Exception:
        pass
    try:
        steps = test_steps or _test_steps.get(pretty_id, [])
        for s in steps:
            sl = s.lower()
            if any(k in sl for k in ["visual", "layout", "pixel", "screenshot", "css", "color"]):
                ui_score += 2
            if any(k in sl for k in ["flow", "scenario", "task", "usability", "accessibility", "a11y"]):
                ux_score += 2
    except Exception:
        pass
    try:
        if driver_obj:
            if "set_window_size" in src_l:
                ui_score += 2
            nav_count = 0
            nav_count += src_l.count(".get(")
            nav_count += src_l.count("current_url")
            if nav_count >= 2:
                ux_score += 2
            if "title" in src_l:
                ux_score += 1
    except Exception:
        pass
    try:
        assert_cnt = src_l.count("assert") if src_l else 0
        if assert_cnt >= 3:
            ux_score += 1
    except Exception:
        pass
    # decision
    if ui_score == 0 and ux_score == 0:
        return ""
    if ui_score >= ux_score + 2:
        return "UI"
    if ux_score >= ui_score + 2:
        return "UX"
    if ui_score > ux_score:
        return "UI"
    if ux_score > ui_score:
        return "UX"
    low_desc = (test_case_desc or "").lower()
    if any(k in low_desc for k in ["layout", "visual", "responsive", "pixel"]):
        return "UI"
    if any(k in low_desc for k in ["flow", "scenario", "task", "journey", "usability"]):
        return "UX"
    return ""


# --------------------------
# Hook: runtest makereport - collect result, screenshot, metadata
# --------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return
    pretty_id = generate_pretty_nodeid(item)
    timestamp = datetime.now().isoformat()
    duration = getattr(rep, "duration", 0.0)
    outcome_str = rep.outcome
    longrepr = ""
    if rep.failed:
        try:
            longrepr = str(rep.longrepr)
        except Exception:
            longrepr = "Failure (longrepr unavailable)"
    browser = item.config.getoption("--browser")
    env = item.config.getoption("--env")
    try:
        test_case_title = getattr(item, "name", None) or item.nodeid.split("::")[-1]
    except Exception:
        test_case_title = item.nodeid
    try:
        test_case_doc = inspect.getdoc(getattr(item, "obj", None)) or ""
    except Exception:
        test_case_doc = ""
    screenshot_path = _test_screenshots.get(pretty_id, "")
    if not screenshot_path:
        driver_obj = getattr(item, "_driver", None) or item.funcargs.get("driver", None) or globals().get("_driver_instance", None)
        print(f"[DEBUG] screenshot attempt for {pretty_id}, driver_obj exists: {bool(driver_obj)}")
        if driver_obj:
            try:
                sc_dir = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(sc_dir, exist_ok=True)
                sc_file = f"{pretty_id}_{RUN_ID}.png"
                screenshot_path = os.path.join(sc_dir, sc_file)
                try:
                    ok = driver_obj.save_screenshot(screenshot_path)
                    print(f"[DEBUG] save_screenshot returned: {ok}")
                except Exception as e:
                    print(f"[DEBUG] save_screenshot raised exception: {e}")
                if not os.path.exists(screenshot_path):
                    try:
                        driver_obj.get_screenshot_as_file(screenshot_path)
                        print("[DEBUG] fallback get_screenshot_as_file succeeded")
                    except Exception as e:
                        print(f"[DEBUG] fallback get_screenshot_as_file failed: {e}")
                if os.path.exists(screenshot_path):
                    _test_screenshots[pretty_id] = screenshot_path
                    print(f"\n[Screenshot saved] {screenshot_path}")
                else:
                    print(f"[DEBUG] screenshot file not found after attempts: {screenshot_path}")
            except Exception as e:
                print(f"[pytest] Failed to capture screenshot in makereport: {e}")
    test_steps = _test_steps.get(pretty_id, [])
    test_case_desc = "\n".join(test_steps) if test_steps else test_case_doc
    meta = extract_metadata_for_item(item, pretty_id)
    if meta.get("title"):
        test_case_title = meta.get("title")
    test_data_raw = meta.get("testdata_raw", "")
    parsed_kv = meta.get("testdata_kv", {})
    priority_value = meta.get("priority", "") or "Medium"
    driver_obj_for_detect = getattr(item, "_driver", None) or item.funcargs.get("driver", None) or globals().get("_driver_instance", None)
    auto_info = auto_detect_type_and_view(item, pretty_id, duration, driver_obj=driver_obj_for_detect, meta=meta, config=item.config)
    category_value = auto_info.get("category", "")
    view_value = meta.get("view") or auto_info.get("view", "")
    page_url_value = auto_info.get("page_url", "")
    page_title_value = auto_info.get("page_title", "")
    # detect UI vs UX
    ui_or_ux = detect_ui_or_ux(item, pretty_id, driver_obj=driver_obj_for_detect, meta=meta, test_steps=test_steps, test_case_desc=test_case_desc)
    result_status = "PASSED" if outcome_str == "passed" else "FAILED"
    # base record
    record = {
        "ID": pretty_id,
        "Test Case Title": test_case_title,
        "Test Case Description": test_case_desc,
        "Precondition": f"{browser.upper()} / {env.upper()}",
        "Test Data": test_data_raw,
        "Expected Output": "Test execution completed",
        "Actual Result": longrepr if longrepr else "No errors",
        "Result": result_status,
        "Priority": priority_value,
        "Duration (s)": f"{duration:.2f}",
        "Browser": browser,
        "Environment": env,
        "Screenshot": screenshot_path,
        "View": view_value,
        "Category": category_value,
        "Page URL": page_url_value,
        "Page Title": page_title_value,
        "UI_or_UX": ui_or_ux
    }
    for k, v in parsed_kv.items():
        col_name = f"TD_{k}"
        record[col_name] = v
    _test_results.append(record)


# --------------------------
# Save to Excel (robust)
# --------------------------
def save_to_excel(df_new, retries=5):
    for attempt in range(retries):
        try:
            df_new.to_excel(TEMP_FILE, index=False, engine="openpyxl")
            if not os.path.exists(MASTER_FILE):
                shutil.move(TEMP_FILE, MASTER_FILE)
                print(f"\n[pytest] Created master file: {MASTER_FILE}")
                return True
            try:
                df_old = pd.read_excel(MASTER_FILE, engine="openpyxl")
                df_all = pd.concat([df_old, df_new], ignore_index=True, sort=False)
            except Exception:
                df_all = df_new
            df_all.to_excel(MASTER_FILE, index=False, engine="openpyxl")
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
            print(f"\n[pytest] Updated master file: {MASTER_FILE}")
            return True
        except PermissionError as e:
            print(f"\n[pytest] Attempt {attempt + 1}/{retries}: File is locked: {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                backup_file = os.path.join(os.getcwd(), f"test_results_backup_{RUN_ID}.xlsx")
                try:
                    df_new.to_excel(backup_file, index=False, engine="openpyxl")
                    print(f"[pytest] Backup file created: {backup_file}")
                    return False
                except Exception as e2:
                    print(f"[pytest] Error creating backup: {e2}")
                    return False
        except Exception as e:
            print(f"\n[pytest] Error when saving master file: {e}")
            return False


# --------------------------
# Session finish: dynamic columns TD_*
# --------------------------
def pytest_sessionfinish(session, exitstatus):
    if not _test_results:
        print("\n[pytest] Không có dữ liệu để lưu.")
        return
    base_columns = [
        "ID",
        "Test Case Title",
        "Test Case Description",
        "Precondition",
        "Test Data",
        "Expected Output",
        "Actual Result",
        "Result",
        "Priority",
        "Duration (s)",
        "Browser",
        "Environment",
        "Screenshot",
        "View",
        "Category",
        "Page URL",
        "Page Title",
        "UI_or_UX"
    ]
    td_cols = set()
    for r in _test_results:
        for k in r.keys():
            if k.startswith("TD_"):
                td_cols.add(k)
    td_cols = sorted(list(td_cols))
    all_columns = base_columns + td_cols
    df_new = pd.DataFrame(_test_results)
    for c in all_columns:
        if c not in df_new.columns:
            df_new[c] = ""
    df_new = df_new[all_columns]
    save_to_excel(df_new)
