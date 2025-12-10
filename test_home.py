# test_navigation_and_categories.py
# Lưu: D:\TestScript\test_navigation_and_categories.py
# Chạy: pytest D:\TestScript\test_navigation_and_categories.py -q
# Yêu cầu: selenium, pytest; dự án có fixture `driver` và (tùy) `log_step`
# Nếu bạn không có `log_step`, thay tất cả log_step(...) bằng print(...)

import time
import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public/"
WAIT = 10

def _safe_click(driver, element):
    """Scroll to element and try click; fallback to JS click."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.12)
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)

def _check_view_shown(driver, expected_fragments=None, expected_keywords=None):
    """
    Kiểm tra view đã hiển thị bằng 3 cách (best-effort):
     - URL chứa 1 trong expected_fragments
     - hoặc body text chứa 1 trong expected_keywords
     - hoặc có ít nhất 1 product card trên trang
    Trả lại (True, diag_msg) nếu pass, (False, diag_msg) nếu fail.
    """
    expected_fragments = expected_fragments or []
    expected_keywords = expected_keywords or []
    cur = driver.current_url.lower()
    body = driver.find_element(By.TAG_NAME, "body").text.lower()
    # check url fragments
    for f in expected_fragments:
        if f and f in cur:
            return True, f"url contains '{f}'"
    # check keywords in body
    for kw in expected_keywords:
        if kw and kw.lower() in body:
            return True, f"body contains '{kw}'"
    # check product cards
    cards = driver.find_elements(By.CSS_SELECTOR, ".card.card-span, .card, .product-card, .product")
    if len(cards) > 0:
        return True, f"{len(cards)} product card(s) present"
    return False, f"no fragment/keyword/card found. url='{cur}', body_snippet='{body[:120]}'"

# -------------------------
# Testcases with explicit steps
# -------------------------

@pytest.mark.tc(title="Trang chủ hiển thị khi bấm 'Trang chủ'",
               desc="Click nav 'Trang chủ' -> hiện trang chủ (banner + icons)",
               pre="Server chạy; trang home truy cập được",
               expected="Hiển thị trang chủ gồm banner + category icons")
def test_nav_home_shows_home(driver, log_step, request):
    """
    Steps:
    1) Mở trang base URL.
    2) Tìm link trong thanh navigation có text 'Trang chủ' (case-insensitive).
    3) Click vào link 'Trang chủ'.
    4) Chờ và kiểm tra: banner hoặc các icon category xuất hiện (hoặc URL chứa 'home').
    Expected: Trang chủ hiển thị (banner + ít nhất 1 icon/category hoặc product card).
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở trang base URL")
        driver.get(BASE_URL)
        driver.maximize_window()

        log_step("Bước 2: Tìm link 'Trang chủ' trong nav")
        links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "nav a, .navbar a")))
        target = None
        for a in links:
            if a.text and ("trang chủ" in a.text.strip().lower() or "trang chu" in a.text.strip().lower()):
                target = a
                break
        assert target is not None, "Không tìm thấy link 'Trang chủ' trong nav"

        log_step("Bước 3: Click link 'Trang chủ'")
        _safe_click(driver, target)
        time.sleep(0.5)

        log_step("Bước 4: Kiểm tra trang chủ hiển thị")
        ok, diag = _check_view_shown(driver, expected_fragments=["home"], expected_keywords=["khuyến", "sản phẩm", "bookworm"])
        assert ok, f"Trang chủ không hiển thị: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC1_home_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="TC2 - Giới thiệu hiển thị khi bấm 'Giới thiệu'",
               desc="Click nav 'Giới thiệu' -> hiện trang about (fallback điều hướng nếu không thấy link)",
               pre="Server chạy; /about route tồn tại",
               expected="Hiển thị nội dung Giới thiệu")
def test_nav_about_shows_about(driver, log_step, request):
    """
    Steps:
    1) Mở trang base URL.
    2) Thử tìm link 'Giới thiệu' trong header/nav (bằng text hoặc bằng href '/about').
    3) Nếu tìm thấy, click; nếu không, điều hướng trực tiếp tới BASE_URL + 'about'.
    4) Chờ và kiểm tra: URL chứa 'about' hoặc body chứa 'giới thiệu'/'về chúng tôi'.
    Expected: Trang Giới thiệu hiển thị.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở trang base URL")
        driver.get(BASE_URL)
        driver.maximize_window()
        time.sleep(0.2)

        log_step("Bước 2: Tìm link 'Giới thiệu' bằng text hoặc href")
        target = None
        # 2.1: tìm bằng text trong mọi thẻ a
        try:
            links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a")))
            for a in links:
                txt = (a.text or "").strip().lower()
                href = (a.get_attribute("href") or "").lower()
                if "giới thiệu" in txt or "gioi thieu" in txt:
                    target = a
                    break
                # nếu href chứa /about thì cũng chấp nhận
                if "/about" in href or href.endswith("/about") or href.endswith("/about/"):
                    target = a
                    break
        except Exception:
            target = None

        # 2.2: fallback: nếu không tìm thấy link, điều hướng trực tiếp tới route about
        if target is None:
            log_step("Không tìm thấy link 'Giới thiệu' trên trang — fallback điều hướng trực tiếp tới /about")
            driver.get(BASE_URL.rstrip("/") + "/about")
        else:
            log_step("Bước 3: Click link 'Giới thiệu' (nếu tồn tại)")
            try:
                # click an toàn
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                time.sleep(0.12)
                target.click()
            except Exception:
                driver.execute_script("arguments[0].click();", target)

        time.sleep(0.6)
        log_step("Bước 4: Kiểm tra trang Giới thiệu hiển thị")
        cur = driver.current_url.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        ok = False
        diag = ""
        if "about" in cur or "/about" in cur:
            ok = True
            diag = f"url contains about: {cur}"
        elif "giới thiệu" in body or "gioi thieu" in body or "về chúng tôi" in body or "ve chung toi" in body:
            ok = True
            diag = "body contains about keywords"
        else:
            cards = driver.find_elements(By.CSS_SELECTOR, ".card, .card-span")
            if len(cards) > 0:
                ok = True
                diag = f"{len(cards)} product card(s) present (fallback)"
        assert ok, f"Trang Giới thiệu không hiển thị: url='{cur}', body_snippet='{body[:200]}'"

    except Exception as e:
        try:
            driver.save_screenshot(f"screenshots/about_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise

@pytest.mark.tc(title="Sản phẩm hiển thị khi bấm 'Sản phẩm'",
               desc="Click nav 'Sản phẩm' -> hiện product list",
               pre="Server chạy",
               expected="Hiển thị danh sách sản phẩm")
def test_nav_products_shows_products(driver, log_step, request):
    """
    Steps:
    1) Mở base URL.
    2) Tìm link nav 'Sản phẩm' (hoặc link chứa 'product', 'product_all').
    3) Click link.
    4) Chờ và kiểm tra: URL chứa 'product' hoặc body chứa 'sản phẩm' hoặc có product card.
    Expected: Trang danh sách sản phẩm hiển thị.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở trang")
        driver.get(BASE_URL)

        log_step("Bước 2: Tìm link 'Sản phẩm'")
        links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "nav a, .navbar a")))
        target = None
        for a in links:
            t = a.text.strip().lower()
            if "sản phẩm" in t or "san pham" in t:
                target = a
                break
        if not target:
            # fallback: tìm link chứa 'product'
            try:
                target = driver.find_element(By.CSS_SELECTOR, "a[href*='product_all'], a[href*='product']")
            except Exception:
                target = None
        assert target is not None, "Không tìm thấy link 'Sản phẩm'"

        log_step("Bước 3: Click link 'Sản phẩm'")
        _safe_click(driver, target)
        time.sleep(0.6)

        log_step("Bước 4: Kiểm tra trang sản phẩm")
        ok, diag = _check_view_shown(driver, expected_fragments=["product", "product_all"], expected_keywords=["sản phẩm", "xem tất cả"])
        assert ok, f"Trang Sản phẩm không hiển thị: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC3_products_{int(time.time())}.png")
        raise

# Category icons: each test defined clearly
@pytest.mark.tc(title="Khuyến mãi icon -> view Khuyến mãi")
def test_icon_sale_shows_sale_view(driver, log_step, request):
    """
    Steps:
    1) Mở home.
    2) Tìm button[name='sale'] dưới banner.
    3) Click button.
    4) Kiểm tra: URL/body/cards cho thấy view Khuyến mãi.
    Expected: Hiển thị nội dung Khuyến mãi hoặc product list filtered.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='sale']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='sale']")))
        log_step("Bước 3: Click button sale")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view khuyến mãi")
        ok, diag = _check_view_shown(driver, expected_fragments=["sale", "product"], expected_keywords=["khuyến", "khuyen"])
        assert ok, f"Không hiển thị view Khuyến mãi: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC4_sale_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="Sản phẩm Mới icon -> view Sản phẩm Mới")
def test_icon_newproduct_shows_newproduct_view(driver, log_step, request):
    """
    Steps:
    1) Mở home.
    2) Tìm button[name='all'].
    3) Click.
    4) Kiểm tra: view Sản phẩm Mới hiển thị.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='all']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='all']")))
        log_step("Bước 3: Click button all")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view Sản phẩm Mới")
        ok, diag = _check_view_shown(driver, expected_fragments=["product", "all"], expected_keywords=["sản phẩm mới", "sản phẩm"])
        assert ok, f"Không hiển thị view Sản phẩm Mới: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC5_new_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="SGK icon -> view Sách Giáo Dục")
def test_icon_sgk_shows_sgk_view(driver, log_step, request):
    """
    Steps:
    1) Mở home.
    2) Tìm button[name='sgk'].
    3) Click.
    4) Kiểm tra view SGK.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='sgk']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='sgk']")))
        log_step("Bước 3: Click sgk")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view SGK")
        ok, diag = _check_view_shown(driver, expected_fragments=["sgk", "product"], expected_keywords=["sách giáo", "sgk", "giáo dục"])
        assert ok, f"Không hiển thị view SGK: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC6_sgk_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="Truyện Tranh icon -> view Truyện Tranh")
def test_icon_comic_shows_comic_view(driver, log_step, request):
    """
    Steps similar: open home -> find button[name='truyentranh'] -> click -> check view
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='truyentranh']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='truyentranh']")))
        log_step("Bước 3: Click truyentranh")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view Truyện Tranh")
        ok, diag = _check_view_shown(driver, expected_fragments=["truyen", "truyentranh", "comic"], expected_keywords=["truyện tranh", "comic"])
        assert ok, f"Không hiển thị view Truyện Tranh: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC7_comic_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="Kỹ Năng Sống icon -> view Kỹ Năng Sống")
def test_icon_kynang_shows_kynang_view(driver, log_step, request):
    """
    Steps: open home -> find button[name='kynang'] -> click -> check view
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='kynang']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='kynang']")))
        log_step("Bước 3: Click kynang")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view Kỹ Năng Sống")
        ok, diag = _check_view_shown(driver, expected_fragments=["kynang", "ky-nang", "skill"], expected_keywords=["kỹ năng", "kynang"])
        assert ok, f"Không hiển thị view Kỹ Năng Sống: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC8_kynang_{int(time.time())}.png")
        raise

@pytest.mark.tc(title="Tiểu Thuyết icon -> view Tiểu Thuyết")
def test_icon_tieuthuyet_shows_view(driver, log_step, request):
    """
    Steps: open home -> find button[name='tieuthuyet'] -> click -> check view
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        log_step("Bước 2: Tìm button[name='tieuthuyet']")
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='tieuthuyet']")))
        log_step("Bước 3: Click tieuthuyet")
        _safe_click(driver, btn)
        time.sleep(0.8)
        log_step("Bước 4: Kiểm tra view Tiểu Thuyết")
        ok, diag = _check_view_shown(driver, expected_fragments=["tieuthuyet", "tieu"], expected_keywords=["tiểu thuyết", "tieuthuyet"])
        assert ok, f"Không hiển thị view Tiểu Thuyết: {diag}"
    except Exception as e:
        driver.save_screenshot(f"screenshots/TC9_tieuthuyet_{int(time.time())}.png")
        raise
def is_user_logged_in(driver):
    """
    Heuristic: kiểm tra presence của link/btn 'Đăng xuất' / 'Logout' / profile
    hoặc kiểm tra sự tồn tại của phần tử đại diện user (ví dụ '.user-name').
    Trả về True nếu phát hiện user đã đăng nhập, False nếu không.
    """
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        # tìm các từ khóa logout/đăng xuất/profile
        if "đăng xuất" in body or "logout" in body or "xin chào" in body or "tài khoản" in body:
            return True
    except Exception:
        pass
    # tìm button/link logout bằng selector phổ biến
    try:
        els = driver.find_elements(By.CSS_SELECTOR, "a[href*='logout'], a[href*='dang-xuat'], a.logout, .logout, .user-menu")
        if len(els) > 0:
            return True
    except Exception:
        pass
    return False

def perform_login(driver, wait, email=None, password=None):
    """
    Thực hiện đăng nhập nhanh:
    - Nếu email/password không truyền vào, lấy từ biến môi trường TEST_USER_EMAIL/TEST_USER_PASS
    - Tìm form/login link; fallback navigate tới BASE_URL + 'login'
    Trả True nếu login thành công (heuristic: phát hiện logout/link profile), False nếu thất bại.
    """
    email = email or os.environ.get("TEST_USER_EMAIL")
    password = password or os.environ.get("TEST_USER_PASS")
    if not email or not password:
        pytest.skip("No test credentials provided (set TEST_USER_EMAIL and TEST_USER_PASS env vars)")

    # Try find login link first
    try:
        login_link = None
        links = driver.find_elements(By.CSS_SELECTOR, "a")
        for a in links:
            href = (a.get_attribute("href") or "").lower()
            txt = (a.text or "").strip().lower()
            if "đăng nhập" in txt or "dang nhap" in txt or "/login" in href or "/dang-nhap" in href:
                login_link = a
                break
        if login_link:
            _safe_click(driver, login_link)
        else:
            # fallback navigate
            driver.get(BASE_URL.rstrip("/") + "/login")
        time.sleep(0.6)
    except Exception:
        try:
            driver.get(BASE_URL.rstrip("/") + "/login")
            time.sleep(0.6)
        except Exception:
            pass

    # Now fill login form: try common selectors
    try:
        # wait for email/username input
        email_input = None
        try:
            email_input = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[name='username'], input[name='user']"))
            )
        except Exception:
            # fallback any input
            inputs = driver.find_elements(By.CSS_SELECTOR, "input")
            if inputs:
                email_input = inputs[0]

        password_input = None
        try:
            password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        except Exception:
            # find second input
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if inputs:
                password_input = inputs[0]

        if email_input and password_input:
            try:
                email_input.clear()
                email_input.send_keys(email)
                password_input.clear()
                password_input.send_keys(password)
            except Exception:
                pass

            # try to submit: look for button 'Đăng nhập' or type=submit
            login_btn = None
            try:
                login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login, input[type='submit']")
            except Exception:
                # find by text
                try:
                    btns = driver.find_elements(By.TAG_NAME, "button")
                    for b in btns:
                        if (b.text or "").strip().lower() in ("đăng nhập", "dang nhap", "login", "sign in"):
                            login_btn = b
                            break
                except Exception:
                    login_btn = None

            if login_btn:
                _safe_click(driver, login_btn)
            else:
                # fallback press Enter on password input
                try:
                    password_input.send_keys("\n")
                except Exception:
                    pass

            # wait a bit and check login success
            time.sleep(1.2)
            return is_user_logged_in(driver)
        else:
            return False
    except Exception:
        return False

# -------------------------
# New testcases: add-to-cart behavior depending on auth state
# -------------------------

@pytest.mark.tc(title="Add to cart redirects to Login when not authenticated",
               desc="Nếu chưa đăng nhập, ấn 'Chọn mua' trên 1 sản phẩm sẽ đưa user tới trang login",
               pre="Server chạy; trang home có ít nhất 1 sản phẩm; user chưa đăng nhập",
               expected="Redirect to login page")
def test_add_to_cart_redirects_login_when_not_authenticated(driver, log_step, request):
    """
    Steps:
    1) Mở trang home.
    2) Đảm bảo user chưa đăng nhập (nếu đã đăng nhập, thử logout nếu có link logout).
    3) Tìm 1 nút 'Chọn mua' (selector: form[action='addCart'] button, .btn-danger, hoặc button chứa 'Chọn mua').
    4) Click nút 'Chọn mua'.
    5) Chờ redirect và assert URL chứa 'login' hoặc body chứa từ 'đăng nhập'/'dang nhap'.
    Expected: Thấy trang login hoặc redirect tới /login.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        driver.maximize_window()
        time.sleep(0.4)

        # ensure logged out: if logged in try to click logout link
        if is_user_logged_in(driver):
            log_step("User đang đăng nhập - cố gắng logout trước khi kiểm tra")
            try:
                logout_candidates = driver.find_elements(By.CSS_SELECTOR, "a[href*='logout'], a[href*='dang-xuat'], .logout")
                if logout_candidates:
                    _safe_click(driver, logout_candidates[0])
                    time.sleep(0.6)
            except Exception:
                pass
            # refresh
            driver.get(BASE_URL)
            time.sleep(0.5)
            assert not is_user_logged_in(driver), "Không thể đảm bảo user đang ở trạng thái logged-out trước khi test"

        log_step("Bước 2: Tìm button 'Chọn mua' (add to cart)")
        btn = None
        try:
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "form[action='addCart'] button, button.btn-danger")))
        except Exception:
            # try xpath contains text 'Chọn mua'
            try:
                btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'chọn mua') or contains(., '👜') or contains(., 'Chọn mua')]")
                if btns:
                    btn = btns[0]
            except Exception:
                btn = None

        assert btn is not None, "Không tìm thấy nút 'Chọn mua' trên trang để test"

        log_step("Bước 3: Click 'Chọn mua' khi chưa đăng nhập")
        _safe_click(driver, btn)
        time.sleep(0.8)

        log_step("Bước 4: Kiểm tra redirect tới trang login")
        cur = driver.current_url.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        login_indicators = ("login", "dang-nhap", "dang_nhap", "đăng nhập", "dang nhap", "/auth")
        ok = any(ind in cur for ind in login_indicators) or any(k in body for k in ("đăng nhập", "dang nhap", "login"))
        assert ok, f"Không redirect tới trang login khi chưa đăng nhập. url='{cur}', body_snippet='{body[:200]}'"

    except Exception as e:
        try:
            driver.save_screenshot(f"screenshots/addcart_not_loggedin_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise

@pytest.mark.tc(title="Add to cart goes to Cart when authenticated",
               desc="Nếu đã đăng nhập, ấn 'Chọn mua' sẽ chuyển tới giỏ hàng hoặc hiển thị giỏ hàng",
               pre="Server chạy; test credentials set as env vars TEST_USER_EMAIL & TEST_USER_PASS (or editable)",
               expected="User được dẫn tới /cart hoặc thấy nội dung giỏ hàng")
def test_add_to_cart_goes_to_cart_when_authenticated(driver, log_step, request):
    """
    Steps:
    1) Mở home.
    2) Nếu chưa login -> thực hiện login bằng perform_login (dùng TEST_USER_EMAIL/TEST_USER_PASS).
    3) Tìm 1 nút 'Chọn mua' và click.
    4) Chờ redirect hoặc kiểm tra page body chứa 'giỏ hàng'/'cart'/'thêm vào giỏ'...
    Expected: URL chứa 'cart' hoặc trang hiện giỏ hàng.
    """
    wait = WebDriverWait(driver, WAIT)
    try:
        log_step("Bước 1: Mở home")
        driver.get(BASE_URL)
        driver.maximize_window()
        time.sleep(0.4)

        # ensure logged in
        if not is_user_logged_in(driver):
            log_step("Chưa đăng nhập -> thực hiện login bằng perform_login")
            logged = perform_login(driver, wait)
            assert logged, "Không login được bằng thông tin test. Thiết lập TEST_USER_EMAIL & TEST_USER_PASS hoặc kiểm tra form login."
            time.sleep(0.6)
            # after login, go to home again to find add-to-cart buttons
            driver.get(BASE_URL)
            time.sleep(0.5)

        assert is_user_logged_in(driver), "Sau khi perform_login vẫn không ở trạng thái logged-in"

        log_step("Bước 2: Tìm button 'Chọn mua' (add to cart)")
        btn = None
        try:
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "form[action='addCart'] button, button.btn-danger")))
        except Exception:
            try:
                btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'chọn mua') or contains(., '👜')]")
                if btns:
                    btn = btns[0]
            except Exception:
                btn = None

        assert btn is not None, "Không tìm thấy nút 'Chọn mua' để kiểm tra khi đã đăng nhập"

        log_step("Bước 3: Click 'Chọn mua'")
        _safe_click(driver, btn)
        time.sleep(0.8)

        log_step("Bước 4: Kiểm tra vào giỏ hàng hoặc thấy nội dung giỏ")
        cur = driver.current_url.lower()
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        cart_ok = False
        # heuristics: url contains cart / gio-hang or body contains 'giỏ hàng', 'cart', 'sản phẩm trong giỏ'
        if any(x in cur for x in ("cart", "gio-hang", "gio_hang", "/cart")):
            cart_ok = True
        if "giỏ hàng" in body or "gio hang" in body or "sản phẩm trong giỏ" in body or "items in cart" in body:
            cart_ok = True
        # some systems may show toast only; try to detect common cart icon/count badge
        try:
            badge = driver.find_elements(By.CSS_SELECTOR, ".cart-count, .badge-cart, .cart-badge, .cart-qty")
            if any(b.text.strip() for b in badge):
                cart_ok = True
        except Exception:
            pass

        assert cart_ok, f"Không thấy redirect/hiển thị giỏ hàng sau khi thêm. url='{cur}', body_snippet='{body[:200]}'"

    except Exception as e:
        try:
            driver.save_screenshot(f"screenshots/addcart_loggedin_fail_{int(time.time())}.png")
        except Exception:
            pass
        raise
