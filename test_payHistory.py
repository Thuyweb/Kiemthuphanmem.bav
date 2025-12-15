import pytest
import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"
VALID_EMAIL = "user@gmail.com" 
VALID_PASS = "123456"

def normalize(text):
    return unicodedata.normalize('NFC', text.strip()) if text else ""

@pytest.fixture(autouse=True)
def setup_driver(driver):
    driver.maximize_window()

def login_step(driver, wait):
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(VALID_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(VALID_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(lambda d: "login" not in d.current_url)

@pytest.mark.tc(
    title="Chức năng Hủy đơn hàng (User)",
    desc="User hủy đơn hàng đang ở trạng thái chờ/đang xử lý thông qua Modal xác nhận",
    pre="User login, có đơn hàng chưa giao (có nút Hủy)",
    expected="Trạng thái đơn hàng đổi thành 'Đã hủy' hoặc 'Canceled'",
    priority="Critical"
)
def test_cancel_order(driver, log_step):
    wait = WebDriverWait(driver, 10)

    log_step("Bước 1: Đăng nhập và vào Lịch sử mua hàng")
    login_step(driver, wait)
    driver.get(f"{BASE_URL}/payHistory")

    log_step("Bước 2: Tìm đơn hàng có nút Hủy")
    try:
        # Tìm nút hủy (class button-cancel hoặc btn-danger)
        cancel_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button-cancel, .btn-danger")))
        log_step("Đã tìm thấy đơn hàng cho phép hủy.")
    except:
        log_step("Không tìm thấy đơn hàng nào có thể hủy.")
        pytest.skip("Không có dữ liệu test phù hợp (nút Hủy).")

    log_step("Bước 3: Click nút Hủy để mở Modal")
    driver.execute_script("arguments[0].click();", cancel_btn)

    log_step("Bước 4: Xác nhận trên Modal (Chọn 'Hủy'/'Đồng ý')")
    try:
        # Chờ modal hiện ra và tìm nút xác nhận (id="cancel" theo code view)
        confirm_btn = wait.until(EC.visibility_of_element_located((By.ID, "cancel")))
        confirm_btn.click()
    except Exception as e:
        pytest.fail(f"Lỗi thao tác Modal: {e}")

    log_step("Bước 5: Kiểm tra trạng thái sau khi hủy")
    time.sleep(2) # Chờ reload
    
    # Kiểm tra lại bảng, tìm chữ "Đã hủy" hoặc "Canceled"
    table_text = normalize(driver.find_element(By.TAG_NAME, "table").text)
    if "Đã hủy" in table_text or "Canceled" in table_text or "CANCELED" in table_text:
        log_step("✔ Trạng thái đơn hàng đã chuyển sang 'Đã hủy'.")
    else:
        pytest.fail("Trạng thái đơn hàng CHƯA thay đổi sau khi hủy.")