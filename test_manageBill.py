import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager 

# --- Cập nhật Biến ---
BASE_URL = "http://localhost/bookstore/public/home"
ORDER_PAGE_URL_EXPECTED = "http://localhost/bookstore/public/manageBill" 
ORDER_PAGE_TITLE_EXPECTED = "Quản lý đơn hàng" 

@pytest.fixture(scope="function")
def driver(request): # Thêm request để đảm bảo tương thích với conftest.py nếu cần
    print("\n[Setup] Mở trình duyệt...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Sử dụng Service của webdriver_manager
    driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(20) 
    
    # Gán driver cho request.node để hook pytest_runtest_makereport trong conftest có thể truy cập
    try:
        request.node._driver = driver
    except Exception:
        pass
        
    yield driver 
    print("\n[Teardown] Đóng trình duyệt...")
    driver.quit()

# Sửa lại hàm login_as_admin để nhận log_step
def login_as_admin(driver, wait, log_step):
    """Thực hiện đăng nhập Admin và ghi log bước."""
    log_step("Precondition: Bắt đầu Đăng nhập Admin")
    driver.get(BASE_URL)
    log_step(f"1. Truy cập trang chủ: {BASE_URL}")
    
    # 1. Click vào nút đăng nhập
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='login']"))).click()
        log_step("2. Click vào nút Đăng nhập trên header.")
    except Exception as e:
        log_step("2. Không tìm thấy nút login (có thể đã đăng nhập), tiếp tục nhập liệu.") 

    # 2. Điền thông tin
    try:
        email = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        email.clear()
        email.send_keys("admin@gmail.com")
        log_step("3. Điền email: admin@gmail.com")
        
        password = driver.find_element(By.NAME, "password")
        password.clear()
        password.send_keys("123123")
        log_step("4. Điền mật khẩu.")
        
        password.send_keys(Keys.RETURN) 
        log_step("5. Nhấn Enter để Đăng nhập.")
        
    except Exception as e:
        log_step(f"Lỗi nhập liệu/form đăng nhập: {e}")
        pytest.fail(f"Lỗi nhập liệu/form đăng nhập: {e}")

    # Chờ xác nhận đăng nhập thành công
    try:
        wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'Admin')] | //a[contains(., 'Đăng xuất')]")))
        log_step("6. Xác nhận Đăng nhập Admin thành công (Thấy menu 'Admin').")
        time.sleep(2) # Chờ 2 giây để đảm bảo menu tải xong
        return True
    except:
        log_step("6. Đăng nhập Admin thất bại (Không thấy menu 'Admin' hoặc 'Đăng xuất').")
        pytest.fail("Đăng nhập Admin thất bại.")
        return False


# THAY ĐỔI: Thêm log_step fixture vào hàm test
def test_odm_001_access_order_management(driver, log_step):
    """
    Title: Kiểm tra truy cập trang Quản lý Đơn Hàng (Admin)
    Description: Admin đăng nhập và điều hướng thành công đến trang quản lý đơn hàng.
    Priority: High
    """
    wait = WebDriverWait(driver, 20) 
    
    # THAY ĐỔI: Truyền log_step vào hàm login
    if not login_as_admin(driver, wait, log_step):
        return
        
    log_step("\n--- Bắt đầu Test Case: Truy cập trang Quản lý Đơn Hàng ---")
    
    # --- Định vị phần tử (Locators) ---
    LOCATOR_MENU_QUAN_LY = (By.XPATH, "//a[contains(., 'Quản Lý')]")
    LOCATOR_SUBMENU_DON_HANG_LINK = (By.CSS_SELECTOR, "a[href*='manageBill']") 

    try:
        # 1. Tìm và CLICK vào menu 'Quản Lý'
        menu_quan_ly = wait.until(
            EC.element_to_be_clickable(LOCATOR_MENU_QUAN_LY),
            "Lỗi: Không tìm thấy hoặc không thể click vào menu 'Quản Lý'."
        )
        menu_quan_ly.click() 
        log_step("7. Click vào menu 'Quản Lý' để hiển thị menu con.")
        
        # 2. Chờ sub-menu 'Đơn Hàng' hiển thị và click
        submenu_don_hang = wait.until(
            EC.presence_of_element_located(LOCATOR_SUBMENU_DON_HANG_LINK),
            "Lỗi: Không tìm thấy link 'Đơn Hàng' trong menu con (sử dụng href=manageBill)."
        )
        
        # SỬ DỤNG JAVASCRIPT CLICK LẠI (GIỮ NGUYÊN LOGIC CŨ)
        driver.execute_script("arguments[0].click();", submenu_don_hang)
        log_step("8. Click vào sub-menu 'Đơn Hàng' (manageBill) bằng JavaScript Click.")
        
        # 3. Kiểm tra kết quả mong muốn
        wait.until(EC.url_to_be(ORDER_PAGE_URL_EXPECTED))
        current_url = driver.current_url
        log_step(f"9. Kiểm tra URL chuyển hướng: {current_url} (Mong đợi: {ORDER_PAGE_URL_EXPECTED})")
        
        # Xác minh URL
        assert current_url == ORDER_PAGE_URL_EXPECTED, \
            f"❌ KẾT QUẢ: FAIL - URL hiện tại '{current_url}' không khớp với URL mong đợi '{ORDER_PAGE_URL_EXPECTED}'."
        
        # 4. Xác minh Tiêu đề trang
        locator_title = (By.XPATH, f"//*[contains(text(), '{ORDER_PAGE_TITLE_EXPECTED}')]")
        wait.until(
            EC.visibility_of_element_located(locator_title),
            f"Lỗi: Không tìm thấy tiêu đề trang '{ORDER_PAGE_TITLE_EXPECTED}' sau khi chuyển hướng."
        )
        log_step(f"10. Xác minh Tiêu đề trang: '{ORDER_PAGE_TITLE_EXPECTED}' đã hiển thị.")
	
	
        log_step("PASSED: Truy cập trang Quản lý Đơn Hàng thành công.")
        print(f"\n✅ KẾT QUẢ: PASS")

    except Exception as e:
        # conftest hook sẽ tự chụp screenshot cho trường hợp FAILED nếu driver còn hoạt động
        log_step(f"FAILED: Đã xảy ra lỗi trong quá trình truy cập Đơn Hàng: {e}")
        pytest.fail("Test Case thất bại.")
	
        
    finally:
        log_step("--- Test Case Kết thúc ---")