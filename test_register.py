import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"

@pytest.fixture(autouse=True)
def setup_driver(driver):
    driver.maximize_window()

@pytest.mark.tc(
    title="Validate Đăng ký: Bỏ trống trường bắt buộc",
    desc="Kiểm tra hệ thống báo lỗi khi người dùng bỏ trống Tên, Email hoặc Mật khẩu",
    pre="Trang đăng ký truy cập được",
    data="Input dữ liệu thiếu 1 trường bất kỳ",
    expected="Không cho phép đăng ký, hiển thị thông báo lỗi hoặc giữ nguyên trang",
    priority="Medium"
)
@pytest.mark.parametrize("field_to_miss", ["name", "email", "password"])
def test_register_validation(driver, log_step, field_to_miss):
    wait = WebDriverWait(driver, 10)
    
    log_step("Bước 1: Truy cập trang Đăng ký")
    driver.get(f"{BASE_URL}/register")
    
    log_step("Bước 2: Điền dữ liệu đầy đủ trước")
    driver.find_element(By.NAME, "name").send_keys("Test User")
    driver.find_element(By.NAME, "email").send_keys(f"test_{int(time.time())}@mail.com")
    driver.find_element(By.NAME, "password").send_keys("123456")
    try:
        driver.find_element(By.NAME, "password_confirmation").send_keys("123456")
    except: pass # Nếu form không có confirm pass thì bỏ qua

    log_step(f"Bước 3: Xóa dữ liệu của trường '{field_to_miss}'")
    input_elem = driver.find_element(By.NAME, field_to_miss)
    input_elem.clear()
    
    log_step("Bước 4: Submit Form")
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", submit_btn)
    
    log_step("Bước 5: Kiểm tra kết quả Validate")
    time.sleep(1) # Chờ phản hồi
    
    # 1. Kiểm tra URL: Nếu vẫn còn chữ 'register' -> Chưa đăng ký thành công -> Pass
    if "register" in driver.current_url:
        log_step("✔ Hệ thống giữ nguyên trang đăng ký (đúng mong đợi).")
    else:
        pytest.fail(f"Lỗi: Hệ thống cho phép đăng ký dù thiếu {field_to_miss}!")

    # 2. Kiểm tra có thông báo lỗi HTML5 hoặc Server không
    try:
        # Check HTML5 validation (browser tooltip)
        is_invalid = driver.execute_script("return arguments[0].validity.valid === false;", input_elem)
        # Check Server validation (text-danger)
        server_error = driver.find_elements(By.CSS_SELECTOR, ".text-danger, .has-error")
        
        if is_invalid or len(server_error) > 0:
            log_step(f"✔ Đã phát hiện thông báo lỗi cho trường {field_to_miss}")
        else:
            log_step("⚠ Không thấy thông báo lỗi rõ ràng, nhưng đã chặn submit.")
    except:
        pass