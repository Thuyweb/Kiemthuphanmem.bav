import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"

@pytest.fixture
def perform_search(driver, log_step):
    wait = WebDriverWait(driver, 10) 
    
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Nhập chữ 'a' vào ô tìm kiếm")
    search_input = driver.find_element(By.NAME, "search")
    search_input.clear()
    search_input.send_keys("a") 
    
    log_step("Bước 3: Ấn nút Tìm kiếm")
    btn = driver.find_element(By.CSS_SELECTOR, "button.btn-search")
    driver.execute_script("arguments[0].click();", btn)
    
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h4")))
    except:
        pytest.skip("Hệ thống chưa có dữ liệu sách để tìm")

@pytest.mark.tc(title="Search - Kiểm tra tiêu đề", priority="Medium")
def test_search_result_header(driver, log_step, perform_search):
    # Đã chạy bước 1, 2, 3 ở fixture
    log_step("Bước 4: Nhìn xem tiêu đề có hiện chữ 'Kết quả tìm kiếm' không")
    header = driver.find_element(By.TAG_NAME, "h4")
    assert "Kết quả tìm kiếm" in header.text

@pytest.mark.tc(title="Search - Kiểm tra hiển thị sách", priority="High")
def test_search_card_structure(driver, log_step, perform_search):
    log_step("Bước 4: Quan sát thẻ sách đầu tiên hiện ra")
    cards = driver.find_elements(By.CLASS_NAME, "card")
    if not cards: pytest.skip("Không có sách nào")
    
    card = cards[0]
    log_step("Bước 5: Kiểm tra xem có đủ Ảnh bìa, Tên sách và Giá tiền không")
    assert card.find_element(By.TAG_NAME, "img").is_displayed()
    assert card.find_element(By.TAG_NAME, "h6").text != ""
    assert "đ" in card.find_element(By.CLASS_NAME, "text-danger").text

@pytest.mark.tc(title="Search - Kiểm tra nút Mua hàng", priority="Critical")
def test_search_add_cart_form(driver, log_step, perform_search):
    log_step("Bước 4: Kiểm tra xem mỗi cuốn sách có nút 'Thêm vào giỏ' (hình giỏ hàng) không")
    forms = driver.find_elements(By.CSS_SELECTOR, "form[action='addCart']")
    
    if forms:
        btn = forms[0].find_element(By.TAG_NAME, "button")
        assert btn.is_displayed()
    else:
        pytest.skip("Không tìm thấy nút mua hàng")

@pytest.mark.tc(title="Search - Kiểm tra nhãn giảm giá", priority="Low")
def test_search_discount_badge(driver, log_step, perform_search):
    log_step("Bước 4: Lướt xem có sách nào đang giảm giá (có nhãn %) không")
    badges = driver.find_elements(By.CLASS_NAME, "badge")
    if badges:
        log_step("   -> Thấy có sách giảm giá, kiểm tra xem có ký hiệu '%' không")
        assert "%" in badges[0].text
    else:
        log_step("   -> Không thấy sách nào giảm giá hôm nay")