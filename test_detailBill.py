import pytest
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"
VALID_EMAIL = "user@gmail.com"  # Cần user có ít nhất 1 đơn hàng
VALID_PASS = "123456"

def normalize(text):
    """Chuẩn hóa tiếng Việt để so sánh chính xác"""
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
    title="Xem chi tiết hóa đơn (Detail Bill)",
    desc="Đăng nhập, vào lịch sử, chọn xem chi tiết đơn hàng đầu tiên và kiểm tra dữ liệu hiển thị",
    pre="Tài khoản user@gmail.com đã có đơn hàng",
    data="TK: user@gmail.com / MK: 123456",
    expected="Chuyển trang detailBill?mhd=X và hiển thị đúng thông tin",
    priority="High"
)
def test_view_detail_bill(driver, log_step):
    wait = WebDriverWait(driver, 10)

    log_step("Bước 1: Đăng nhập hệ thống")
    try:
        login_step(driver, wait)
        log_step(f"Đăng nhập thành công với {VALID_EMAIL}")
    except Exception as e:
        pytest.fail(f"Lỗi đăng nhập: {e}")

    log_step("Bước 2: Truy cập menu 'Lịch sử mua hàng'")
    driver.get(f"{BASE_URL}/payHistory")
    
    log_step("Bước 3: Lấy ID đơn hàng đầu tiên để đối chiếu")
    try:
        # Lấy mã hóa đơn ở dòng đầu tiên
        first_row = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr:nth-child(1)")))
        bill_id = first_row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
        log_step(f"Chọn đơn hàng số: {bill_id}")
    except:
        pytest.skip("Không có đơn hàng nào trong lịch sử để test.")

    log_step("Bước 4: Click icon 'Xem chi tiết' (hình con mắt)")
    try:
        view_btn = first_row.find_element(By.CSS_SELECTOR, "a[href*='detailBill']")
        driver.execute_script("arguments[0].click();", view_btn)
    except Exception as e:
        pytest.fail(f"Không click được nút xem chi tiết: {e}")

    log_step("Bước 5: Kiểm tra URL và nội dung trang Chi tiết")
    wait.until(EC.url_contains("detailBill"))
    
    # Check URL
    current_url = driver.current_url
    assert f"mhd={bill_id}" in current_url, f"URL sai. Kỳ vọng mhd={bill_id}, thực tế: {current_url}"
    
    # Check Tiêu đề
    header = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h4"))).text
    assert bill_id in header, f"Tiêu đề không chứa mã đơn hàng {bill_id}"
    
    # Check các trường thông tin bắt buộc
    body_text = normalize(driver.find_element(By.TAG_NAME, "body").text)
    required_info = ["Trạng thái đơn hàng", "Trạng thái thanh toán", "THÀNH TIỀN"]
    for info in required_info:
        assert normalize(info) in body_text, f"Thiếu thông tin trên giao diện: {info}"
        
    log_step(f"✔ Đã hiển thị đúng chi tiết hóa đơn {bill_id}")