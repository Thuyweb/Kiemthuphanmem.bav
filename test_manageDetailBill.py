import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Cấu hình URL
BASE_URL = "http://localhost/bookstore/public"
LOGIN_URL = f"{BASE_URL}/home" 

# --- Cập nhật Fixture driver (Thêm request để tương thích với conftest) ---
@pytest.fixture(scope="function")
def driver(request):
    """Khởi tạo và đóng trình duyệt Chrome."""
    print("\n[Setup] Khởi tạo trình duyệt...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    
    # Gán driver cho request.node để hook pytest_runtest_makereport trong conftest có thể truy cập
    try:
        request.node._driver = driver
    except Exception:
        pass
        
    yield driver
    print("\n[Teardown] Đóng trình duyệt...")
    try:
        driver.quit()
    except:
        pass


@pytest.fixture(scope="function")
# THAY ĐỔI: Thêm log_step vào fixture để ghi lại quá trình đăng nhập
def admin_logged_in_driver(driver, log_step):
    """
    Fixture này tự động đăng nhập với quyền Admin 
    và trả về driver đã đăng nhập cho test case sử dụng.
    """
    wait = WebDriverWait(driver, 10)
    
    log_step("Precondition: Bắt đầu Đăng nhập Admin")
    
    # 1. Vào trang Login
    driver.get(LOGIN_URL)
    log_step(f"1. Truy cập trang chủ: {LOGIN_URL}")
    
    # 2. Click nút Login và điền thông tin
    try:
        # Cố gắng click vào nút login
        try:
            login_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='login']")))
            login_link.click()
            log_step("2. Click vào nút Đăng nhập trên header.")
        except:
            log_step("2. Nút Login không khả dụng/không tìm thấy, tiếp tục nhập liệu.")
            pass
        
        # Điền thông tin đăng nhập
        wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys("admin@gmail.com")
        log_step("3. Điền email: admin@gmail.com")
        
        pwd = driver.find_element(By.NAME, "password")
        pwd.clear()
        pwd.send_keys("123123")
        log_step("4. Điền mật khẩu.")
        
        # Gửi form
        pwd.send_keys(Keys.RETURN)
        log_step("5. Nhấn Enter để Đăng nhập.")
        
        # Chờ sau khi đăng nhập xong (kiểm tra sự xuất hiện của menu Quản Lý)
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Quản Lý')]")))
        log_step("6. Xác nhận Đăng nhập Admin thành công (Thấy menu 'Quản Lý').")
        print("\n✅ Đăng nhập Admin thành công.")
    except Exception as e:
        log_step(f"❌ Đăng nhập Admin thất bại: {e}")
        pytest.fail(f"❌ Đăng nhập Admin thất bại: {e}")
        
    return driver # Trả về driver đã đăng nhập


@pytest.mark.tc(
    title="Xem chi tiết đơn hàng (Admin)",
    priority="High",
    view="Bill Detail", # Đổi từ 'Bill Detail Redirect' sang 'Bill Detail' cho ngắn gọn
    test_type="UX" # Thử phân loại là UX vì liên quan đến flow người dùng
)
# THAY ĐỔI: Thêm log_step vào hàm test
def test_view_bill_detail(admin_logged_in_driver, log_step):
    """
    Kiểm tra chức năng xem chi tiết đơn hàng (Admin): 
    1. Điều hướng đến trang Quản lý Đơn hàng.
    2. Click vào nút 'Chi Tiết' của đơn hàng đầu tiên.
    3. Xác nhận URL chuyển hướng đúng sang /manageDetailBill?mhd=<ID>.
    """
    driver = admin_logged_in_driver
    wait = WebDriverWait(driver, 10)
    
    log_step("--- Bắt đầu Test Case: Xem chi tiết đơn hàng ---")
    
    # 1. Điều hướng đến trang Quản lý Đơn hàng
    manage_bill_url = f"{BASE_URL}/manageBill"
    log_step(f"7. Điều hướng đến trang Quản lý Đơn hàng: {manage_bill_url}")
    driver.get(manage_bill_url)
    
    # Chờ bảng đơn hàng tải xong (chờ nút 'Chi Tiết' đầu tiên)
    detail_icon_xpath = "//table/tbody/tr[1]/td/a[contains(@href, 'manageDetailBill')]"
    
    try:
        log_step("8. Tìm nút 'Chi Tiết' (icon info) của đơn hàng đầu tiên.")
        detail_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, detail_icon_xpath)),
            "Lỗi: Không tìm thấy nút 'Chi Tiết' cho đơn hàng đầu tiên."
        )
        
    except Exception as e:
        log_step("8. Không tìm thấy đơn hàng nào để kiểm tra (Hoặc không thấy nút 'Chi Tiết').")
        pytest.skip(f"Không có đơn hàng nào để kiểm tra chi tiết: {e}")
        return

    # Lấy mã đơn hàng (mhd) hiện tại từ thuộc tính href
    current_href = detail_button.get_attribute("href")
    
    if "mhd=" not in current_href:
        log_step("Lỗi: Không tìm thấy tham số 'mhd' trong đường dẫn chi tiết đơn hàng.")
        pytest.fail("Không tìm thấy tham số 'mhd' trong đường dẫn chi tiết đơn hàng.")
        
    bill_id = current_href.split("mhd=")[-1]
    
    log_step(f"9. Đã lấy được mã đơn hàng (mhd): {bill_id}.")
    
    # 2. Click vào nút Chi Tiết
    detail_button.click()
    log_step("10. Click vào nút 'Chi Tiết'.")
    
    # 3. Xác nhận chuyển hướng URL
    expected_url_part = f"/manageDetailBill?mhd={bill_id}"
    
    # Chờ URL chứa phần mong muốn
    wait.until(EC.url_contains(expected_url_part))
    
    # 4. KIỂM TRA ĐƯỜNG DẪN ĐÚNG
    final_url = driver.current_url
    
    log_step(f"11. Kiểm tra URL cuối cùng: {final_url}")
    
    # Kiểm tra URL đầy đủ, bao gồm cả BASE_URL
    assert final_url == f"{BASE_URL}{expected_url_part}", \
        f"URL cuối cùng không chính xác.\n" \
        f"Mong muốn: {BASE_URL}{expected_url_part}\n" \
        f"Thực tế:  {final_url}"
        
    log_step(f"PASSED: URL chuyển hướng chính xác đến chi tiết đơn hàng {bill_id}.")
    log_step("--- Test Case Kết thúc ---")