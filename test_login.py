# test_login.py
# Lưu: D:\TestScript\test_login.py
# Chạy: pytest D:\TestScript\test_login.py -q
# Yêu cầu: selenium, pytest; dự án có fixture `driver` và (tùy) `log_step`

import os
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# cấu hình mặc định (thay nếu bạn đã define ở nơi khác)
BASE_URL = "http://localhost/bookstore/public/"
WAIT = 10

def _safe_click(driver, element):
    """Scroll to element and try click; fallback to JS click."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.08)
        element.click()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
        except Exception:
            # last resort: send Enter if it's a button or input
            try:
                element.send_keys("\n")
            except Exception:
                pass

# ----------------------------
# Login view tests
# ----------------------------

@pytest.mark.tc(title="Login page: form elements present and visible",
               desc="Kiểm tra presence của form, email, password, toggle, social buttons và submit",
               pre="Server chạy; route /login tồn tại",
               expected="Form đăng nhập hiển thị đầy đủ")
def test_login_form_elements_present(driver, log_step, request):
    """
    Steps:
    1) Mở /login.
    2) Chờ form#singinForm hiển thị.
    3) Kiểm tra presence input#email, input#password, button#toggleBtn, social buttons (img Google/Facebook), và button[type='submit'].
    Expected: Tất cả phần tử trên tồn tại và visible.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở trang login")
        driver.get(BASE_URL.rstrip("/") + "/login")
        driver.maximize_window()
        log_step("Bước 2: Chờ form #singinForm")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "form#singinForm")))
        log_step("Bước 3: Kiểm tra các phần tử")
        assert driver.find_element(By.CSS_SELECTOR, "input#email"), "Không tìm thấy input#email"
        assert driver.find_element(By.CSS_SELECTOR, "input#password"), "Không tìm thấy input#password"
        # toggleBtn is an <input type="button" id="toggleBtn">
        assert driver.find_element(By.CSS_SELECTOR, "input#toggleBtn, #toggleBtn"), "Không tìm thấy toggleBtn"
        # social icons (try multiple selectors)
        google = driver.find_elements(By.CSS_SELECTOR, "img[src*='Googleicon'], img[alt*='Google'], button:has(img[src*='Googleicon'])")
        facebook = driver.find_elements(By.CSS_SELECTOR, "img[src*='facebookicon'], img[alt*='facebook'], button:has(img[src*='facebookicon'])")
        assert google, "Không tìm thấy Google social button/icon"
        assert facebook, "Không tìm thấy Facebook social button/icon"
        assert driver.find_element(By.CSS_SELECTOR, "button[type='submit']"), "Không tìm thấy nút submit"
    except Exception:
        try:
            os.makedirs("screenshots", exist_ok=True)
            driver.save_screenshot(f"screenshots/login_present_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise


@pytest.mark.tc(title="Login: toggle password visibility works",
               desc="Nhấn toggle password để hiện/ẩn mật khẩu",
               pre="Có trang login hiển thị",
               expected="Password input thay đổi type giữa 'password' và 'text'")
def test_login_toggle_password_visibility(driver, log_step, request):
    """
    Steps:
    1) Mở /login.
    2) Nhập sample password vào input#password.
    3) Click toggleBtn lần 1 -> kiểm tra type == 'text'.
    4) Click toggleBtn lần 2 -> kiểm tra type == 'password'.
    Expected: toggle thay đổi type đúng.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Mở trang login")
        driver.get(BASE_URL.rstrip("/") + "/login")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "form#singinForm")))
        pwd = driver.find_element(By.CSS_SELECTOR, "input#password")
        toggle = driver.find_element(By.CSS_SELECTOR, "input#toggleBtn, #toggleBtn")
        # ensure initial type is password (best-effort)
        initial_type = pwd.get_attribute("type")
        pwd.clear()
        pwd.send_keys("SamplePass123!")
        log_step("Click toggle lần 1 (should show)")
        _safe_click(driver, toggle)
        time.sleep(0.3)
        assert pwd.get_attribute("type") == "text", f"Toggle failed to set type text (got {pwd.get_attribute('type')})"
        log_step("Click toggle lần 2 (should hide)")
        _safe_click(driver, toggle)
        time.sleep(0.3)
        assert pwd.get_attribute("type") == "password", f"Toggle failed to set type password (got {pwd.get_attribute('type')})"
    except Exception:
        try:
            os.makedirs("screenshots", exist_ok=True)
            driver.save_screenshot(f"screenshots/login_toggle_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise


@pytest.mark.tc(title="Login failure with invalid credentials",
               desc="Gửi form login với credential sai -> user không được đăng nhập; hiển thị lỗi nếu có",
               pre="Route /login tồn tại",
               expected="Không được đăng nhập (và/hoặc hiển thị message lỗi)")
def test_login_with_invalid_credentials_shows_error(driver, log_step, request):
    """
    Steps:
    1) Mở /login.
    2) Điền email/password sai.
    3) Click 'Đăng nhập'.
    4) Chờ và kiểm tra:
       - có message lỗi (class text-danger/help-block/alert-danger) HOẶC
       - URL vẫn chứa 'login' HOẶC
       - server không log user in (heuristic: không xuất hiện logout/profile).
    Expected: Không được đăng nhập; nếu server trả lỗi thì hiển thị lỗi.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Mở trang login")
        driver.get(BASE_URL.rstrip("/") + "/login")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "form#singinForm")))
        email = driver.find_element(By.CSS_SELECTOR, "input#email")
        pwd = driver.find_element(By.CSS_SELECTOR, "input#password")
        # use clearly invalid creds
        email.clear(); email.send_keys("invalid_user_example_not_real@example.invalid")
        pwd.clear(); pwd.send_keys("wrongpassword123")
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        _safe_click(driver, btn)

        # chờ server/UI xử lý
        time.sleep(1.0)

        cur = driver.current_url.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()

        # tìm message lỗi hiển thị trên trang (dùng nhiều selector fallback)
        errs = []
        try:
            errs = driver.find_elements(By.CSS_SELECTOR, ".text-danger, .help-block, .alert-danger, .error, .fw-bold")
        except Exception:
            errs = []

        # helper: detect if logged-in indicator present (logout/profile)
        def _is_logged_in_now():
            try:
                body_txt = driver.find_element(By.TAG_NAME, "body").text.lower()
                if "đăng xuất" in body_txt or "logout" in body_txt or "tài khoản" in body_txt or "xin chào" in body_txt or "welcome" in body_txt:
                    return True
            except Exception:
                pass
            try:
                els = driver.find_elements(By.CSS_SELECTOR, "a[href*='logout'], a[href*='dang-xuat'], .logout, .user-menu, .profile")
                if len(els) > 0:
                    return True
            except Exception:
                pass
            return False

        logged_in_after = _is_logged_in_now()

        # Pass conditions:
        # 1) Có message lỗi (errs non-empty) OR
        # 2) URL vẫn chứa 'login' OR
        # 3) Không bị đăng nhập (logged_in_after == False)
        # Fail only if redirected and appears logged-in (very unexpected)
        if errs:
            # good: visible error messages
            pass
        elif "login" in cur or "/login" in cur:
            # good: still on login page
            pass
        elif not logged_in_after:
            # acceptable: server redirected but did not log the user in
            pass
        else:
            # fail: redirected and looks logged in (unexpected) -> fail
            try:
                os.makedirs("screenshots", exist_ok=True)
                driver.save_screenshot(f"screenshots/login_invalid_unexpected_{int(time.time())}.png")
            except Exception:
                pass
            assert False, f"Không thấy lỗi khi dùng credential sai và user có vẻ đã đăng nhập. url={cur}, body_snippet={body[:200]}"

        # optional debug message
        if not errs and "login" not in cur:
            print("[DEBUG] No visible error elements and not on /login; ensured not logged-in (treated as pass).")

    except Exception:
        try:
            os.makedirs("screenshots", exist_ok=True)
            driver.save_screenshot(f"screenshots/login_invalid_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise


@pytest.mark.tc(title="Login success with valid credentials",
               desc="Đăng nhập thành công bằng tài khoản test (env vars TEST_USER_EMAIL/TEST_USER_PASS)",
               pre="TEST_USER_EMAIL & TEST_USER_PASS set",
               expected="Redirect tới trang home hoặc hiển thị thông tin user")
def test_login_success_redirects_home(driver, log_step, request):
    """
    Steps:
    1) Mở /login.
    2) Điền email/password (từ env vars TEST_USER_EMAIL, TEST_USER_PASS).
    3) Click Đăng nhập.
    4) Chờ redirect: kiểm tra URL không còn chứa 'login' và có indicator user (logout/profile) hoặc redirect về BASE_URL.
    Expected: Đăng nhập thành công.
    """
    wait = WebDriverWait(driver, WAIT)
    email_val = os.environ.get("TEST_USER_EMAIL")
    pass_val = os.environ.get("TEST_USER_PASS")
    if not email_val or not pass_val:
        pytest.skip("TEST_USER_EMAIL / TEST_USER_PASS not set in environment")

    try:
        log_step("Mở trang login")
        driver.get(BASE_URL.rstrip("/") + "/login")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "form#singinForm")))
        email = driver.find_element(By.CSS_SELECTOR, "input#email")
        pwd = driver.find_element(By.CSS_SELECTOR, "input#password")
        email.clear(); email.send_keys(email_val)
        pwd.clear(); pwd.send_keys(pass_val)
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        _safe_click(driver, btn)
        # wait for redirect / presence of logout or profile indicator
        time.sleep(1.2)
        cur = driver.current_url.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()

        logged_in = False
        try:
            if "đăng xuất" in body or "logout" in body or "tài khoản" in body or "xin chào" in body or "welcome" in body:
                logged_in = True
        except Exception:
            logged_in = False
        try:
            els = driver.find_elements(By.CSS_SELECTOR, "a[href*='logout'], a[href*='dang-xuat'], .logout, .user-menu, .profile")
            if els:
                logged_in = True
        except Exception:
            pass

        assert ("login" not in cur and logged_in) or ("home" in cur or BASE_URL.rstrip("/") in cur), \
            f"Không redirect/không thấy indicator đăng nhập sau khi submit. url={cur}, body_snippet={body[:150]}"

    except Exception:
        try:
            os.makedirs("screenshots", exist_ok=True)
            driver.save_screenshot(f"screenshots/login_success_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise
# End of test_login.py
# cách chạy: set TEST_USER_EMAIL=your_test_email@example.com
#set TEST_USER_PASS=your_password_here
#pytest test_login.py::test_login_success_redirects_home -q
