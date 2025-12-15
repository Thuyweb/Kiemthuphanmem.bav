import pytest
import time
import re # Thư viện regex để làm sạch chuỗi mạnh mẽ hơn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException

# Cấu hình URL
BASE_URL = "http://localhost/bookstore/public"
LOGIN_URL = f"{BASE_URL}/home" 
MANAGE_BILL_URL = f"{BASE_URL}/manageBill" # URL trang quản lý đơn hàng

# Hàm làm sạch chuỗi bằng Regex: Loại bỏ mọi ký tự không phải chữ cái và số, sau đó trim
def clean_text(text):
    """
    Làm sạch chuỗi bằng cách loại bỏ mọi ký tự không phải chữ cái, số, tiếng Việt, 
    sau đó thay thế nhiều khoảng trắng bằng một khoảng trắng duy nhất, và strip.
    Ví dụ: ' Hoà n th \xa0 à nh ' -> 'Hoàn thành'
    """
    if not isinstance(text, str):
        return ""
    # Thay thế mọi ký tự không phải chữ cái, số, tiếng Việt, hoặc khoảng trắng thành khoảng trắng
    # Bao gồm cả các ký tự đặc biệt, non-breaking space, vv.
    cleaned = re.sub(r'[^\w\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĐđ]', ' ', text)
    # Thay thế các chuỗi khoảng trắng/dấu cách lớn hơn 1 bằng 1 khoảng trắng duy nhất
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

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
def admin_logged_in_driver(driver, log_step): # THÊM log_step
    """
    Fixture này tự động đăng nhập với quyền Admin 
    và trả về driver đã đăng nhập cho test case sử dụng.
    """
    wait = WebDriverWait(driver, 10)
    
    log_step(f"Di chuyển đến trang đăng nhập: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    
    try:
        # Cố gắng click vào nút login
        try:
            log_step("Cố gắng click vào link/nút 'login'")
            login_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='login']")))
            login_link.click()
        except:
            log_step("Link 'login' không cần thiết (đã ở trang login hoặc đã có form). Tiếp tục điền form.")
            pass
        
        # Điền thông tin đăng nhập
        log_step("Điền thông tin đăng nhập: email=admin@gmail.com, password=123123")
        wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys("admin@gmail.com")
        pwd = driver.find_element(By.NAME, "password")
        pwd.clear()
        pwd.send_keys("123123")
        pwd.send_keys(Keys.RETURN)
        
        # Chờ sau khi đăng nhập xong (kiểm tra sự xuất hiện của menu Quản Lý)
        log_step("Chờ menu 'Quản Lý' xuất hiện để xác nhận đăng nhập thành công.")
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Quản Lý')]")))
        print("\n✅ Đăng nhập Admin thành công.")
        log_step("Đăng nhập Admin thành công.")
    except Exception as e:
        log_step(f"Lỗi: Đăng nhập Admin thất bại: {e}")
        pytest.fail(f"❌ Đăng nhập Admin thất bại: {e}")
        
    return driver # Trả về driver đã đăng nhập

# ==========================================
# TEST CASE 1: HỦY ĐƠN HÀNG BỊ TỪ CHỐI (Ấn 'Không' trong Modal)
# ==========================================
@pytest.mark.tc(title="Hủy đơn hàng - Từ chối hành động trong modal", priority="High")
def test_cancel_order_dismiss_modal(admin_logged_in_driver, log_step): # THÊM log_step
    driver = admin_logged_in_driver 
    wait = WebDriverWait(driver, 20)
    
    log_step(f"Di chuyển đến trang Quản Lý Đơn Hàng: {MANAGE_BILL_URL}")
    driver.get(MANAGE_BILL_URL) 
    print("\n--- TEST 1: HỦY ĐƠN HÀNG BỊ TỪ CHỐI (Tắt Modal) ---")
    
    target_row = None
    order_id = None
    initial_status = None
    
    try:
        log_step("Tìm kiếm đơn hàng có nút 'Hủy Đơn' khả dụng.")
        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr")))
        
        # 1. Tìm đơn hàng có nút Hủy Đơn
        for row in rows:
            try:
                # Nút Hủy Đơn nằm trong cột Thao Tác (td[6])
                btn_cancel = row.find_element(By.XPATH, "./td[6]//button[contains(text(), 'Hủy Đơn')]")
                order_id = row.find_element(By.XPATH, "./td[1]").text
                
                # Lấy trạng thái ban đầu và làm sạch bằng clean_text
                raw_initial_status = row.find_element(By.XPATH, "./td[5]").text
                initial_status = clean_text(raw_initial_status)
                target_row = row
                break
            except:
                continue
        
        if not target_row:
            log_step("Không tìm thấy đơn hàng nào có thể hủy.")
            pytest.skip("⚠️ SKIPPED: Không tìm thấy đơn hàng nào có thể hủy.")
            return
        
        log_step(f"Đã tìm thấy Đơn hàng ID {order_id}. Trạng thái ban đầu: '{initial_status}'")
        print(f" -> Đơn hàng ID {order_id} có trạng thái ban đầu: '{initial_status}'")

        # 2. Click nút "Hủy Đơn"
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_cancel)
        time.sleep(0.5)
        btn_cancel.click()
        log_step("Click nút 'Hủy Đơn' trên dòng đơn hàng.")

        # 3. Chờ Modal xác nhận và click "Không" (Nút từ chối trong modal)
        modal = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'modal-content')]"))) 
        
        btn_dismiss_in_modal = modal.find_element(By.XPATH, ".//button[text()='Không']") # Nút Không
            
        btn_dismiss_in_modal.click()
        log_step("Click nút 'Không' trong Modal xác nhận.")
        print(" -> Đã click nút 'Không' (Từ chối).")

        # 4. Verify: Modal đã biến mất
        log_step("Chờ Modal xác nhận biến mất.")
        wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'modal-content')]")))

        # 5. Verify: Trạng thái đơn hàng KHÔNG THAY ĐỔI
        log_step(f"Kiểm tra lại trạng thái của Đơn hàng ID {order_id}.")
        updated_row = wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//table/tbody/tr/td[1][text()='{order_id}']/..")
        ))
        
        raw_new_status = updated_row.find_element(By.XPATH, "./td[5]").text
        new_status = clean_text(raw_new_status) # Làm sạch trạng thái mới
        
        if new_status == initial_status:
            log_step(f"SUCCESS: Trạng thái đơn hàng giữ nguyên: '{new_status}'")
            print(f"🎉 SUCCESS: Đơn hàng ID {order_id} giữ nguyên trạng thái: '{new_status}'")
        else:
            log_step(f"FAILED: Trạng thái đã bị thay đổi. Ban đầu: '{initial_status}', Hiện tại: '{new_status}'")
            driver.save_screenshot("fail_dismiss_modal.png")
            pytest.fail(f"❌ FAILED: Trạng thái đơn hàng ID {order_id} đã bị thay đổi. Ban đầu: '{initial_status}', Hiện tại: '{new_status}'")

    except Exception as e:
        log_step(f"Lỗi xảy ra trong Test Case: {e}")
        driver.save_screenshot("error_dismiss_modal_fail.png")
        pytest.fail(f"❌ Lỗi Test Hủy Đơn Hàng Bị Từ Chối (Modal): {e}")


# ==========================================
# TEST CASE 2: HỦY ĐƠN HÀNG THÀNH CÔNG (Kiểm tra cột THAO TÁC là 'Hoàn thành')
# ==========================================
@pytest.mark.tc(title="Hủy đơn hàng - Xác nhận hành động trong modal", priority="High")
def test_confirm_cancel_order_success(admin_logged_in_driver, log_step): # THÊM log_step
    driver = admin_logged_in_driver 
    wait = WebDriverWait(driver, 10) 
    
    log_step(f"Di chuyển đến trang Quản Lý Đơn Hàng: {MANAGE_BILL_URL}")
    driver.get(MANAGE_BILL_URL) 
    print("\n--- TEST 2: HỦY ĐƠN HÀNG THÀNH CÔNG (Kiểm tra cột THAO TÁC) ---")
    
    target_row = None
    order_id = None
    
    try:
        log_step("Tìm kiếm đơn hàng có nút 'Hủy Đơn' khả dụng.")
        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr")))
        
        # 1. Tìm đơn hàng có nút Hủy Đơn (Sử dụng XPath linh hoạt)
        for row in rows:
            try:
                btn_cancel = row.find_element(By.XPATH, "./td[6]//button[contains(text(), 'Hủy Đơn')]")
                order_id = row.find_element(By.XPATH, "./td[1]").text
                target_row = row
                break
            except:
                continue
        
        if not target_row:
            log_step("Không tìm thấy đơn hàng nào có thể hủy.")
            pytest.skip("⚠️ SKIPPED: Không tìm thấy đơn hàng nào có thể hủy.")
            return

        log_step(f"Đã tìm thấy Đơn hàng ID {order_id}.")
        
        # 2. Click nút "Hủy Đơn"
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_cancel)
        time.sleep(0.5)
        btn_cancel.click()
        log_step("Click nút 'Hủy Đơn' trên dòng đơn hàng.")

        # 3. Chờ Modal xác nhận và click "Hủy" (Nút xác nhận trong modal)
        modal = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'modal-content')]"))) 
        
        btn_confirm_in_modal = modal.find_element(By.XPATH, ".//button[text()='Hủy']") # Nút Hủy màu hồng/đỏ
            
        btn_confirm_in_modal.click()
        log_step("Click nút 'Hủy' (xác nhận) trong modal.")
        print(" -> Đã click nút 'Hủy' (xác nhận) trong modal.")

        # 4. CHỜ CỘT THAO TÁC CẬP NHẬT thành 'Hoàn thành'
        action_cell_locator = (By.XPATH, f"//table/tbody/tr/td[1][text()='{order_id}']/../td[6]")
        expected_text_clean = "Hoa n tha nh" # Giá trị làm sạch được mong đợi

        log_step(f"Chờ cột THAO TÁC của ĐH {order_id} chuyển thành '{expected_text_clean}' (dạng làm sạch).")
        print(f" -> Đang chờ cột THAO TÁC của ĐH {order_id} chuyển thành '{expected_text_clean}' trong {wait._timeout} giây...")

        try:
            # Custom wait sử dụng hàm clean_text mạnh mẽ
            wait.until(lambda d: 
                clean_text(d.find_element(*action_cell_locator).text) == expected_text_clean
            )
            
            # Lấy giá trị cuối cùng để báo cáo SUCCESS
            final_action_raw = driver.find_element(*action_cell_locator).text
            final_action_clean = clean_text(final_action_raw)
            
            log_step(f"SUCCESS: Cột THAO TÁC đã cập nhật thành '{final_action_clean}'")
            print(f"🎉 SUCCESS: Đơn hàng ID {order_id} đã được hủy thành công. Cột THAO TÁC: '{final_action_clean}'")
            
        except TimeoutException:
            # Nếu hết thời gian chờ
            current_action_clean = "Không thể lấy giá trị"
            try:
                # Cố gắng lấy trạng thái hiện tại lần cuối để báo cáo lỗi
                current_action_raw = driver.find_element(*action_cell_locator).text
                current_action_clean = clean_text(current_action_raw)
            except:
                pass 
            
            log_step(f"FAILED: Hết thời gian chờ. Cột THAO TÁC hiện tại: '{current_action_clean}'")
            driver.save_screenshot("fail_cancel_success.png")
            pytest.fail(f"❌ FAILED: Đơn hàng ID {order_id} không chuyển sang '{expected_text_clean}' trong {wait._timeout} giây. Hiện tại: '{current_action_clean}'")

    except Exception as e:
        log_step(f"Lỗi xảy ra trong Test Case: {e}")
        driver.save_screenshot("error_cancel_order_confirm.png")
        pytest.fail(f"❌ Lỗi Test Hủy Đơn Hàng Thành Công: {e}")