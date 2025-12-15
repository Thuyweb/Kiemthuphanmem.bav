import pytest
import time
import re 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Cấu hình URL
BASE_URL = "http://localhost/bookstore/public"
LOGIN_URL = f"{BASE_URL}/home" 
MANAGE_BILL_URL = f"{BASE_URL}/manageBill" # URL trang quản lý đơn hàng

# ==========================================
# HÀM HỖ TRỢ ĐÃ ĐƯỢC FIX LỖI KHOẢNG TRẮNG
# ==========================================
def clean_text(text):
    """
    Làm sạch chuỗi bằng cách loại bỏ các ký tự đặc biệt, sau đó 
    chuẩn hóa về khoảng trắng duy nhất và loại bỏ ký tự ngắt dòng/tab.
    """
    if not isinstance(text, str):
        return ""
    
    # Loại bỏ các ký tự không phải chữ cái, số, hoặc khoảng trắng (bao gồm cả ký tự đặc biệt như \xa0)
    # flag re.UNICODE để hỗ trợ tốt hơn cho tiếng Việt
    cleaned = re.sub(r'[^\w\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĐđ]', ' ', text, flags=re.UNICODE)
    
    # Thay thế tất cả các chuỗi khoảng trắng (bao gồm cả \n, \t, \xa0) bằng một khoảng trắng duy nhất
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Loại bỏ khoảng trắng ở đầu và cuối chuỗi
    return cleaned.strip()


# Hàm chụp màn hình (thêm để debug tốt hơn)
def save_screenshot(driver, test_id, description="debug"):
    """Lưu screenshot với tên file có timestamp và ID test."""
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Giả định có thư mục screenshots hoặc thư mục hiện tại
        filename = f"screenshots/{test_id}_{timestamp}_{description}.png" 
        driver.save_screenshot(filename)
        print(f"[DEBUG] Screenshot saved: {filename}")
        return True
    except Exception as e:
        print(f"[DEBUG] Could not save screenshot: {e}")
        return False


@pytest.fixture(scope="function")
def driver():
    """Khởi tạo và đóng trình duyệt Chrome."""
    print("\n[Setup] Khởi tạo trình duyệt...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    yield driver
    print("\n[Teardown] Đóng trình duyệt...")
    try:
        driver.quit()
    except:
        pass


@pytest.fixture(scope="function")
def admin_logged_in_driver(driver, log_step): # <-- ĐÃ THÊM log_step
    """
    Fixture này tự động đăng nhập với quyền Admin 
    và trả về driver đã đăng nhập cho test case sử dụng.
    """
    wait = WebDriverWait(driver, 10)
    
    log_step(f"Di chuyển đến trang đăng nhập: {LOGIN_URL}") # <-- THÊM LOG STEP
    driver.get(LOGIN_URL)
    
    try:
        # Cố gắng click vào nút login (nếu chưa ở trang login)
        try:
            log_step("Cố gắng click vào link/nút 'login'") # <-- THÊM LOG STEP
            login_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='login']")))
            login_link.click()
        except:
            log_step("Link 'login' không cần thiết (đã ở trang login hoặc đã có form). Tiếp tục điền form.") # <-- THÊM LOG STEP
            pass
        
        # Điền thông tin đăng nhập
        log_step("Điền thông tin đăng nhập: email=admin@gmail.com, password=123123") # <-- THÊM LOG STEP
        wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys("admin@gmail.com")
        pwd = driver.find_element(By.NAME, "password")
        pwd.clear()
        pwd.send_keys("123123")
        pwd.send_keys(Keys.RETURN)
        
        # Chờ sau khi đăng nhập xong (kiểm tra sự xuất hiện của menu Quản Lý)
        log_step("Chờ menu 'Quản Lý' xuất hiện để xác nhận đăng nhập thành công.") # <-- THÊM LOG STEP
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Quản Lý')]")))
        print("\n✅ Đăng nhập Admin thành công.")
        log_step("Đăng nhập Admin thành công.") # <-- THÊM LOG STEP
    except Exception as e:
        log_step(f"Lỗi: Đăng nhập Admin thất bại: {e}") # <-- THÊM LOG STEP
        pytest.fail(f"❌ Đăng nhập Admin thất bại: {e}")
        
    return driver # Trả về driver đã đăng nhập


# ==========================================
# TEST CASE: GỬI ĐƠN HÀNG THÀNH CÔNG (Đã Fix Lỗi)
# ==========================================
@pytest.mark.tc(title="Gửi đơn hàng (chuyển trạng thái sang Đang vận chuyển)", priority="High", view="Manage Bills") # <-- ĐÃ THÊM MARKER
def test_confirm_send_order_success(admin_logged_in_driver, log_step): # <-- ĐÃ THÊM log_step
    driver = admin_logged_in_driver 
    # Tăng thời gian chờ lên 20s
    wait = WebDriverWait(driver, 20) 
    
    log_step(f"Di chuyển đến trang Quản Lý Đơn Hàng: {MANAGE_BILL_URL}") # <-- THÊM LOG STEP
    driver.get(MANAGE_BILL_URL) 
    test_id = "TM-T534_Final_Accurate" 
    print("\n--- TEST 1: Gửi đơn hàng (Chỉ tìm nút Gửi Đơn bằng CSS Class) ---")
    
    target_row = None
    order_id = None
    
    try:
        log_step("Chờ bảng đơn hàng tải xong.") # <-- THÊM LOG STEP
        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr")))
        
        # 1. Tìm đơn hàng có nút Gửi Đơn (Không cần kiểm tra trạng thái ban đầu)
        btn_send = None
        log_step("Tìm kiếm đơn hàng có nút 'Gửi Đơn' (class: btn-success) khả dụng.") # <-- THÊM LOG STEP
        for row in rows:
            try:
                # CỘT THAO TÁC là td[6]
                # Sử dụng XPath tìm thẻ <button> có class chứa 'btn-success' (nút màu xanh lá)
                xpath_send_button = "./td[6]//button[contains(@class, 'btn-success')]"

                # Cố gắng tìm nút Gửi Đơn
                btn_send = row.find_element(By.XPATH, xpath_send_button)
                
                # Nếu tìm thấy nút:
                order_id = row.find_element(By.XPATH, "./td[1]").text
                target_row = row
                break # Tìm thấy đơn hàng phù hợp -> Dừng lại
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        
        if not target_row:
            log_step("Không tìm thấy đơn hàng nào có thể gửi đi (nút 'Gửi Đơn' không hiển thị).") # <-- THÊM LOG STEP
            pytest.skip(f"⚠️ SKIPPED: Không tìm thấy đơn hàng nào có nút 'Gửi Đơn' (class: btn-success) trong cột Thao tác.")
            return
        
        log_step(f"Đã tìm thấy Đơn hàng ID {order_id} có thể gửi đi.") # <-- THÊM LOG STEP
        print(f" -> Đơn hàng ID {order_id} được chọn để Gửi Đơn.")

        # 2. Click nút "Gửi Đơn"
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_send)
        time.sleep(0.5)
        btn_send.click()
        log_step(f"Click nút 'Gửi Đơn' trên dòng đơn hàng ID {order_id}.") # <-- THÊM LOG STEP

        
        # 3. CHỜ CỘT TRẠNG THÁI CẬP NHẬT thành 'Đang vận chuyển'
        # Cột TRẠNG THÁI là td[5]
        action_cell_locator = (By.XPATH, f"//table/tbody/tr/td[1][text()='{order_id}']/../td[5]")
        expected_status = "Đang vâ n chuyê n" 

        log_step(f"Chờ cột TRẠNG THÁI của ĐH {order_id} cập nhật thành '{expected_status}' (dạng làm sạch).") # <-- THÊM LOG STEP
        print(f" -> Đang chờ cột TRẠNG THÁI của ĐH {order_id} chuyển thành '{expected_status}' trong {wait._timeout} giây...")

        try:
            # Custom wait sử dụng hàm clean_text đã fix
            wait.until(lambda d: 
                clean_text(d.find_element(*action_cell_locator).text) == expected_status)

            # Lấy giá trị cuối cùng để báo cáo SUCCESS
            final_status_raw = driver.find_element(*action_cell_locator).text 
            final_status_clean = clean_text(final_status_raw)
            
            log_step(f"SUCCESS: Trạng thái đơn hàng đã cập nhật thành: '{final_status_clean}'") # <-- THÊM LOG STEP
            print(f"🎉 SUCCESS: Đơn hàng ID {order_id} đã được gửi thành công. Trạng thái mới: '{final_status_clean}'")
            
        except TimeoutException:
            # Nếu hết thời gian chờ
            current_status_clean = "Không thể lấy giá trị"
            try:
                current_status_raw = driver.find_element(*action_cell_locator).text 
                current_status_clean = clean_text(current_status_raw)
            except:
                pass 
                
            save_screenshot(driver, test_id, "FAILED_status_update")
            log_step(f"FAILED: Hết thời gian chờ. Trạng thái hiện tại: '{current_status_clean}'") # <-- THÊM LOG STEP
            # Thêm thông báo giúp người dùng debug dễ hơn
            pytest.fail(f"❌ FAILED: Đơn hàng ID {order_id} không chuyển sang '{expected_status}' trong {wait._timeout} giây. Hiện tại: '{current_status_clean}' (Kiểm tra lại trạng thái cuối cùng hoặc hàm clean_text)")

    except Exception as e:
        save_screenshot(driver, test_id, "ERROR_during_test")
        log_step(f"Lỗi xảy ra trong Test Case: {e}") # <-- THÊM LOG STEP
        pytest.fail(f"❌ Lỗi Test Gửi Đơn Hàng Thành Công: {e}")