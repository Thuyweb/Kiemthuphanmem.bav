# test_loc.py
import pytest
import time
import re 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select # <<< IMPORT Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager 

# ==========================================
# CẤU HÌNH VÀ HÀM TIỆN ÍCH
# ==========================================

# Cấu hình URL
BASE_URL = "http://localhost/bookstore/public"
LOGIN_URL = f"{BASE_URL}/home" 
MANAGE_BILL_URL = f"{BASE_URL}/manageBill" # URL trang quản lý đơn hàng

# HÀM LÀM SẠCH CHUỖI ĐÃ TỐI ƯU HÓA
def clean_text(text):
    """
    Làm sạch chuỗi bằng cách loại bỏ mọi ký tự không phải chữ cái, số, tiếng Việt và khoảng trắng, 
    sau đó chuẩn hóa tất cả khoảng trắng về một khoảng trắng duy nhất.
    """
    if not isinstance(text, str):
        return ""
    
    # 1. Tăng cường loại bỏ ký tự lạ (như \xa0, \ufeff, và các ký tự không hiển thị)
    cleaned = text.replace('\xa0', ' ').replace('\u200b', '')
    
    # 2. Loại bỏ các ký tự không phải chữ cái, số, tiếng Việt, hoặc khoảng trắng tiêu chuẩn
    cleaned = re.sub(r'[^\w\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĐđ]', '', cleaned, flags=re.UNICODE)
    
    # 3. Chuẩn hóa tất cả các chuỗi khoảng trắng lớn hơn 1 thành một khoảng trắng duy nhất
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # 4. Loại bỏ khoảng trắng ở đầu và cuối chuỗi
    return cleaned.strip()


# Hàm chụp màn hình (Giữ nguyên, nhưng nên dùng cơ chế trong conftest)
def save_screenshot(driver, test_id, description="debug"):
    """Lưu screenshot với tên file có timestamp và ID test."""
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Sử dụng thư mục và định dạng tên file tương thích với conftest để tránh xung đột
        filename = f"screenshots/{test_id}_{timestamp}_{description}.png"
        os.makedirs("screenshots", exist_ok=True)
        driver.save_screenshot(filename)
        print(f"[DEBUG] Screenshot saved: {filename}")
        return True
    except Exception as e:
        print(f"[DEBUG] Could not save screenshot: {e}")
        return False

# Fixture driver (Cập nhật để sử dụng ChromeDriverManager)
@pytest.fixture(scope="function")
def driver():
    """Khởi tạo và đóng trình duyệt Chrome."""
    print("\n[Setup] Khởi tạo trình duyệt...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Sử dụng ChromeDriverManager
    driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=options)
    yield driver
    print("\n[Teardown] Đóng trình duyệt...")
    try:
        driver.quit()
    except:
        pass


@pytest.fixture(scope="function")
def admin_logged_in_driver(driver, log_step): # <<< THÊM log_step
    """
    Fixture này tự động đăng nhập với quyền Admin 
    và trả về driver đã đăng nhập cho test case sử dụng.
    """
    wait = WebDriverWait(driver, 10)
    
    log_step("Bắt đầu đăng nhập Admin qua fixture (Precondition).")
    
    # 1. Vào trang Login và đăng nhập
    driver.get(LOGIN_URL)
    log_step(f"Truy cập URL: {LOGIN_URL}")
    
    try:
        # Cố gắng click vào nút login (nếu chưa ở trang login)
        try:
            login_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='login']")))
            login_link.click()
            log_step("Click vào nút 'Đăng nhập' (nav link).")
        except:
            log_step("Không tìm thấy nút login, giả định đã ở trang login hoặc tiếp tục nhập liệu.")
            pass
        
        # Điền thông tin đăng nhập
        wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys("admin@gmail.com")
        log_step("Nhập Email: admin@gmail.com")
        pwd = driver.find_element(By.NAME, "password")
        pwd.clear()
        pwd.send_keys("123123")
        log_step("Nhập Mật khẩu.")
        pwd.send_keys(Keys.RETURN)
        log_step("Gửi form đăng nhập (nhấn ENTER).")
        
        # Chờ sau khi đăng nhập xong
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Quản Lý')]")))
        log_step("✅ Đăng nhập Admin thành công.")
    except Exception as e:
        log_step(f"❌ Đăng nhập Admin thất bại: {e}")
        pytest.fail(f"❌ Đăng nhập Admin thất bại: {e}")
        
    return driver # Trả về driver đã đăng nhập


# ==========================================
# TEST CASE: LỌC ĐƠN HÀNG THEO TRẠNG THÁI 
# ==========================================

# Tham số: (Tên trạng thái trong dropdown, Tên trạng thái hiển thị trong cột TRẠNG THÁI (hoặc None))
FILTER_CASES = [
    ("1", "Tất cả đơn hàng", None),
    ("2", "Đang chuẩn bị hàng", "Đang chuân bi hang"),
    ("3", "Đang vận chuyển", "Đang vân chuyên"),
    ("4", "Đã hoàn tất", "Đơn hang đa hoan tât"),
    ("5", "Đã hủy", "Đa huy"),
]

@pytest.mark.parametrize("option_value, dropdown_status, expected_status_text", FILTER_CASES)
@pytest.mark.tc(
    title="Lọc đơn hàng theo trạng thái",
    priority="Medium",
    view="Manage Bills",
    test_type="Functional" # Loại test này là Functional
)
def test_filter_bill_by_status(admin_logged_in_driver, log_step, option_value, dropdown_status, expected_status_text): # <<< THÊM log_step
    driver = admin_logged_in_driver 
    wait = WebDriverWait(driver, 10)
    test_id = f"TF-{dropdown_status.replace(' ', '_')}"
    
    log_step(f"--- TEST: Lọc Đơn Hàng theo '{dropdown_status}' (Value={option_value}) ---")
    
    driver.get(MANAGE_BILL_URL) 
    log_step(f"1. Truy cập trang Quản lý Đơn Hàng: {MANAGE_BILL_URL}")
    
    # Ghi lại dữ liệu test
    log_step(f"Test Data: Status='{dropdown_status}'; Value='{option_value}'; ExpectedText='{expected_status_text}'")
    
    try:
        # 2. TÌM VÀ CHỌN TÙY CHỌN TRONG <SELECT>
        
        select_locator = (By.NAME, "bill-filter")
        
        # Chờ thẻ select hiển thị
        select_element = wait.until(
            EC.presence_of_element_located(select_locator),
            "Không tìm thấy thẻ <select name='bill-filter'>."
        )
        
        select = Select(select_element)
        
        # Chọn Option bằng giá trị (Value) của thẻ <option>
        select.select_by_value(option_value) 
        
        log_step(f"2. Đã chọn filter: {dropdown_status} (Value={option_value}).")
        
        # 3. Chờ cho bảng cập nhật
        # Chờ 3 giây để form submit và trang reload/tải dữ liệu mới
        time.sleep(3) 
        log_step("3. Chờ 3 giây để dữ liệu mới tải xong sau khi áp dụng filter.")

        # 4. Kiểm tra kết quả
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
        log_step(f"4. Đã tìm thấy {len(rows)} hàng sau khi lọc.")
        
        if dropdown_status == "Tất cả đơn hàng":
            if len(rows) > 0:
                log_step(f"✅ KẾT QUẢ: PASS - Lọc '{dropdown_status}' thành công. Tìm thấy {len(rows)} đơn hàng.")
            else:
                save_screenshot(driver, test_id, "FILTER_FAIL_NO_DATA_ALL")
                pytest.fail(f"❌ FAILED: Lọc '{dropdown_status}' không tìm thấy đơn hàng nào.")
        
        else:
            if not rows:
                log_step(f"✅ PASSED: Lọc '{dropdown_status}' không tìm thấy đơn hàng nào (Đúng nếu không có đơn hàng nào ở trạng thái này).")
                return

            # Duyệt qua tất cả các hàng, kiểm tra cột trạng thái (td[5])
            all_match = True
            mismatch_count = 0
            
            for i, row in enumerate(rows):
                try:
                    status_cell = row.find_element(By.XPATH, "./td[5]")
                    # SỬ DỤNG clean_text đã fix để làm sạch trạng thái thực tế
                    actual_status = clean_text(status_cell.text) 

                    if actual_status != expected_status_text:
                        all_match = False
                        mismatch_count += 1
                        # Ghi log lỗi chi tiết
                        log_step(f" [LỖI HÀNG {i+1}]: Trạng thái thực tế: '{actual_status}' != Trạng thái mong muốn: '{expected_status_text}'")
                        if mismatch_count > 3:
                            log_step("Dừng kiểm tra hàng do đã có 3 lỗi không khớp.")
                            break
                            
                except NoSuchElementException:
                    all_match = False
                    log_step(f" [LỖI HÀNG {i+1}]: Không tìm thấy cột trạng thái (td[5]).")
                except Exception as e:
                    log_step(f" [LỖI HÀNG {i+1}]: Lỗi khi đọc hàng: {e}")

            if all_match:
                log_step(f"✅ KẾT QUẢ: PASS - Lọc '{dropdown_status}' thành công. Tất cả {len(rows)} đơn hàng đều có trạng thái '{expected_status_text}'.")
            else:
                save_screenshot(driver, test_id, "FILTER_FAIL_MISMATCH")
                pytest.fail(f"❌ FAILED: Lọc '{dropdown_status}' thất bại. Tổng số hàng: {len(rows)}. Số hàng không khớp: {mismatch_count}")

    except TimeoutException:
        save_screenshot(driver, test_id, "TIMEOUT_ERROR")
        log_step("❌ Lỗi Timeout: Không tìm thấy thẻ <select name='bill-filter'> trong 10 giây.")
        pytest.fail(f"❌ Lỗi Timeout: Không tìm thấy thẻ <select name='bill-filter'> trong 10 giây.")
    except Exception as e:
        save_screenshot(driver, test_id, "GENERAL_ERROR")
        log_step(f"❌ Lỗi chung khi test lọc '{dropdown_status}': {e}")
        pytest.fail(f"❌ Lỗi chung khi test lọc '{dropdown_status}': {e}")
        
    finally:
        log_step("--- Test Case Kết thúc ---")