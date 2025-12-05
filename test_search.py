# test_search.py
import os
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.mark.tc(title="Tìm kiếm sách 'Đắc Nhân Tâm'",
               desc="Kiểm tra chức năng tìm kiếm với từ khóa có dấu",
               pre="Server localhost đang chạy; trang bookstore/public/ truy cập được",
               data="keyword=Đắc nhân tâm",
               expected="Hiển thị kết quả chứa 'Đắc nhân tâm'",
               priority="High")
def test_search_dac_nhan_tam(driver, log_step, request):
    """
    Title: Tìm kiếm sách Đắc Nhân Tâm
    Description: Kiểm tra tìm kiếm hiển thị sản phẩm liên quan
    Precondition: Server running, trang home sẵn sàng
    TestData: keyword=Đắc nhân tâm
    Expected: Kết quả chứa 'Đắc nhân tâm'
    """
    wait = WebDriverWait(driver, 10)
    expected_title = "đắc nhân tâm"

    # helper lưu screenshot khi lỗi (tên file lấy từ nodeid)
    def _save_screenshot_on_error(prefix="error"):
        try:
            sc_dir = os.path.join(os.getcwd(), "screenshots")
            os.makedirs(sc_dir, exist_ok=True)
            # sanitize nodeid -> thay kí tự không hợp lệ bằng _
            nodeid = request.node.nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")
            filename = f"{prefix}_{nodeid}_{int(time.time())}.png"
            path = os.path.join(sc_dir, filename)
            driver.save_screenshot(path)
            print(f"[DEBUG] Saved screenshot: {path}")
            return path
        except Exception as e:
            print(f"[DEBUG] Fail to save screenshot: {e}")
            return ""

    try:
        # 1) Mở trang chủ
        log_step("Bước 1: Mở trang chủ")
        driver.get("http://localhost/bookstore/public/")
        driver.maximize_window()

        # 2) Click icon kính lúp để hiện ô tìm kiếm (chờ icon xuất hiện)
        log_step("Bước 2: Click icon tìm kiếm")
        # dùng nhiều selector để tăng độ bền: có thể là fa-search hoặc fa-magnifying-glass
        search_icon = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "i.fa-search, i.fa-magnifying-glass, .btn-search, .icon-search")
        ))
        search_icon.click()

        # 3) Chờ input tìm kiếm hiển thị và nhập từ khóa
        log_step("Bước 3: Nhập từ khóa tìm kiếm")
        search_input = wait.until(EC.visibility_of_element_located((By.NAME, "search")))
        search_input.clear()
        search_input.send_keys("Đắc nhân tâm")
        search_input.send_keys(Keys.ENTER)

        # 4) Chờ kết quả load: presence của header kết quả hoặc card
        log_step("Bước 4: Chờ kết quả hiển thị")
        # ví dụ header kết quả là h4
        result_header = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h4")))
        assert result_header and result_header.text, "Header kết quả rỗng hoặc không tồn tại"

        # 5) Lấy danh sách tên sách trên trang kết quả
        log_step("Bước 5: Kiểm tra danh sách sách trả về")
        product_titles = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h6.card-title a, .product-title, .card-title a")))

        # normalize text to compare
        texts = [t.text.strip().lower() for t in product_titles if t.text.strip()]
        assert texts, "Không tìm thấy phần tử tiêu đề sách trên trang kết quả."

        # 6) Kiểm tra ít nhất một title chứa expected_title
        assert any(expected_title in t for t in texts), \
            f"Không tìm thấy sách '{expected_title.title()}' trong kết quả tìm kiếm! Danh sách trả về: {texts}"

    except Exception as e:
        # lưu screenshot để debug rồi raise lại để pytest ghi fail
        _save_screenshot_on_error("fail")
        # in stack trace ngắn
        print(f"[ERROR] Test failed: {e}")
        raise
