# conftest.py (sửa: luôn chụp ảnh cho cả pass/fail, gán driver lên node, debug prints)
import os
import re
import time
import shutil
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


def pytest_addoption(parser):
    parser.addoption("--browser", default="chrome")
    parser.addoption("--env", default="local")


def generate_pretty_nodeid(item):
    """
    Chuyển nodeid thành mã chuyên nghiệp: test_search.py::test_x -> TS-T123
    """
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


# Fixture để test ghi bước
@pytest.fixture
def log_step(request):
    pretty_id = generate_pretty_nodeid(request.node)
    _test_steps.setdefault(pretty_id, [])
    def _log(step_text):
        _test_steps[pretty_id].append(step_text)
    return _log


# Helper: cố gắng chụp screenshot, trả về path or ""
def try_capture_screenshot_for_pretty_id(pretty_id, driver_obj=None):
    """
    Thử chụp ảnh. Nếu driver_obj None, fallback tới global _driver_instance.
    Trả về đường dẫn file nếu thành công, else "".
    """
    global _driver_instance
    screenshot_path = ""
    try:
        if not driver_obj:
            driver_obj = globals().get("_driver_instance", None)

        if not driver_obj:
            print(f"[DEBUG] No driver available to take screenshot for {pretty_id}")
            return ""

        # debug info
        try:
            sid = getattr(driver_obj, "session_id", None)
            print(f"[DEBUG] Taking screenshot for {pretty_id}, session_id={sid}")
        except Exception:
            pass

        sc_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(sc_dir, exist_ok=True)
        sc_file = f"{pretty_id}_{RUN_ID}.png"
        screenshot_path = os.path.join(sc_dir, sc_file)

        # main attempt
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
            print(f"[DEBUG] Screenshot file not found after save attempt: {screenshot_path}")
            return ""
    except Exception as e:
        print(f"[DEBUG] Unexpected error when capturing screenshot: {e}")
        return ""


# Driver fixture: lưu driver lên request.node để makereport dễ truy cập
@pytest.fixture
def driver(request):
    global _driver_instance
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        raise RuntimeError(f"Cannot import selenium/webdriver_manager: {e}")

    # khởi tạo Chrome (bạn có thể thêm options nếu muốn headless)
    driver_inst = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    _driver_instance = driver_inst

    # Lưu driver trực tiếp trên node để makereport có thể lấy được
    try:
        request.node._driver = driver_inst
    except Exception:
        pass

    pretty_id = generate_pretty_nodeid(request.node)

    yield driver_inst

    # Teardown: cố gắng chụp screenshot (nếu chưa có) - đảm bảo có ảnh ngay cả khi test pass
    try:
        if pretty_id not in _test_screenshots:
            path = try_capture_screenshot_for_pretty_id(pretty_id, driver_inst)
            if path:
                _test_screenshots[pretty_id] = path
    except Exception as e:
        print(f"[DEBUG] Error during driver teardown screenshot: {e}")

    try:
        driver_inst.quit()
    except Exception:
        pass

    _driver_instance = None


# Hook: thu thập kết quả và ghi record
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    # chỉ xử lý phase "call"
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

    # --- attempt to capture screenshot (always, not only on failure) ---
    screenshot_path = _test_screenshots.get(pretty_id, "")
    if not screenshot_path:
        # try multiple ways to obtain driver
        driver_obj = getattr(item, "_driver", None)  # from fixture set on node
        if not driver_obj:
            driver_obj = item.funcargs.get("driver", None)
        if not driver_obj:
            driver_obj = globals().get("_driver_instance", None)

        print(f"[DEBUG] screenshot attempt for {pretty_id}, driver_obj exists: {bool(driver_obj)}")
        if driver_obj:
            try:
                sc_dir = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(sc_dir, exist_ok=True)
                sc_file = f"{pretty_id}_{RUN_ID}.png"
                screenshot_path = os.path.join(sc_dir, sc_file)

                # try save and report results
                try:
                    ok = driver_obj.save_screenshot(screenshot_path)
                    print(f"[DEBUG] save_screenshot returned: {ok}")
                except Exception as e:
                    print(f"[DEBUG] save_screenshot raised exception: {e}")

                # fallback
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

    # lấy các bước log (nếu có)
    test_steps = _test_steps.get(pretty_id, [])
    test_case_desc = "\n".join(test_steps) if test_steps else test_case_doc

    result_status = "PASSED" if outcome_str == "passed" else "FAILED"

    record = {
        "ID": pretty_id,
        "Test Case Title": test_case_title,
        "Test Case Description": test_case_desc,
        "Precondition": f"{browser.upper()} / {env.upper()}",
        "Test Data": "",
        "Expected Output": "Test execution completed",
        "Actual Result": longrepr if longrepr else "No errors",
        "Result": result_status,
        "Priority": "Medium",
        "Duration (s)": f"{duration:.2f}",
        "Browser": browser,
        "Environment": env,
        "Screenshot": screenshot_path
    }

    _test_results.append(record)


# Save to Excel (robust, với temp file & retry)
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


def pytest_sessionfinish(session, exitstatus):
    if not _test_results:
        print("\n[pytest] Không có dữ liệu để lưu.")
        return

    columns = [
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
        "Screenshot"
    ]

    df_new = pd.DataFrame(_test_results)
    for c in columns:
        if c not in df_new.columns:
            df_new[c] = ""
    df_new = df_new[columns]
    save_to_excel(df_new)
        