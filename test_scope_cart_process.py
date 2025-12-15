import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"

@pytest.fixture
def ensure_cart_has_item(driver, log_step):
    wait = WebDriverWait(driver, 15)
    
    # Chuẩn bị dữ liệu
    log_step("Chuẩn bị: Đăng nhập tài khoản User")
    driver.get(f"{BASE_URL}/login")
    try:
        driver.find_element(By.NAME, "email").send_keys("duy123@gmail.com")
        driver.find_element(By.NAME, "password").send_keys("duy123")
        driver.find_element(By.ID, "singinForm").submit()
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout')]")))
    except:
        pytest.fail("Không đăng nhập được để test giỏ hàng")

    log_step("Chuẩn bị: Tìm một cuốn sách và thêm vào giỏ")
    try:
        driver.find_element(By.NAME, "search").send_keys("a")
        driver.find_element(By.CSS_SELECTOR, "button.btn-search").click()
        
        add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "form[action='addCart'] button")))
        add_btn.click()
        time.sleep(2) 
    except:
        pytest.skip("Lỗi khi thêm hàng vào giỏ (có thể hết sách)")

@pytest.mark.tc(title="Cart - Kiểm tra bảng giỏ hàng", priority="Medium")
def test_cart_table_headers(driver, log_step, ensure_cart_has_item):
    log_step("Bước 1: Ấn vào icon Giỏ hàng để xem chi tiết")
    driver.get(f"{BASE_URL}/cart")
    
    log_step("Bước 2: Nhìn bảng danh sách, kiểm tra có đủ các cột: Tên sách, Số lượng, Giá, Tổng tiền")
    headers = driver.find_elements(By.CSS_SELECTOR, "thead th")
    header_text = "".join([h.text for h in headers]).upper()
    
    assert "SẢN PHẨM" in header_text
    assert "SỐ LƯỢNG" in header_text
    assert "TIỀN" in header_text

@pytest.mark.tc(title="Cart - Kiểm tra chức năng cập nhật", priority="Medium")
def test_cart_update_form(driver, log_step, ensure_cart_has_item):
    log_step("Bước 1: Vào trang Giỏ hàng")
    driver.get(f"{BASE_URL}/cart")
    
    log_step("Bước 2: Kiểm tra xem có ô nhập số lượng và nút cập nhật/xóa không")
    form = driver.find_element(By.CSS_SELECTOR, "form[action='updateCart']")
    assert form.is_displayed()

@pytest.mark.tc(title="Cart - Kiểm tra popup xác nhận", priority="High")
def test_cart_modal_structure(driver, log_step, ensure_cart_has_item):
    driver.get(f"{BASE_URL}/cart")
    wait = WebDriverWait(driver, 5)
    
    log_step("Bước 1: Ấn nút 'Đặt hàng'")
    btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bs-target='#confirm-pay']")))
    btn.click()
    
    log_step("Bước 2: Kiểm tra popup xác nhận có hiện lên không")
    modal = wait.until(EC.visibility_of_element_located((By.ID, "confirm-pay")))
    assert "Xác nhận đặt hàng" in modal.text

@pytest.mark.tc(title="Cart - Thử nút Hủy", priority="Medium")
def test_cart_modal_cancel(driver, log_step, ensure_cart_has_item):
    driver.get(f"{BASE_URL}/cart")
    wait = WebDriverWait(driver, 5)
    
    log_step("Bước 1: Ấn nút 'Đặt hàng' để mở popup")
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#confirm-pay']").click()
    
    log_step("Bước 2: Ấn nút 'Hủy' (hoặc Đóng) trên popup")
    modal = wait.until(EC.visibility_of_element_located((By.ID, "confirm-pay")))
    modal.find_element(By.CSS_SELECTOR, "button.btn-secondary").click()
    
    log_step("Bước 3: Kiểm tra xem popup có đóng lại chưa")
    wait.until(EC.invisibility_of_element_located((By.ID, "confirm-pay")))

@pytest.mark.tc(title="Pay - Luồng thanh toán", priority="High")
def test_pay_page_elements(driver, log_step, ensure_cart_has_item):
    wait = WebDriverWait(driver, 10)
    driver.get(f"{BASE_URL}/cart")
    
    log_step("Bước 1: Ấn nút 'Đặt hàng'")
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#confirm-pay']").click()
    
    log_step("Bước 2: Ấn 'Xác nhận' trên popup để chốt đơn")
    modal = wait.until(EC.visibility_of_element_located((By.ID, "confirm-pay")))
    modal.find_element(By.CSS_SELECTOR, "button.btn-primary[type='submit']").click()
    
    log_step("Bước 3: Chờ chuyển sang trang thông báo thành công")
    wait.until(EC.url_contains("pay"))
    
    log_step("Bước 4: Kiểm tra xem có dòng chữ 'Thành công' và hình ảnh xác nhận không")
    h4 = driver.find_element(By.TAG_NAME, "h4")
    assert "thành công" in h4.text or "Success" in h4.text