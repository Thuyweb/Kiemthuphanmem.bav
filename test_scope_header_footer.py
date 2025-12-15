import pytest
from selenium.webdriver.common.by import By

BASE_URL = "http://localhost/bookstore/public"

# --- HEADER ---

@pytest.mark.tc(title="Header - Kiểm tra Topbar", priority="Low")
def test_header_topbar_display(driver, log_step):
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Nhìn lên thanh trên cùng (Topbar) xem có mục 'FAQs' hay 'Help' không")
    topbar = driver.find_element(By.CSS_SELECTOR, ".bg-primary.py-3")
    assert topbar.is_displayed()
    assert "FAQs" in topbar.text or "Help" in topbar.text

@pytest.mark.tc(title="Header - Kiểm tra ô tìm kiếm", priority="Medium")
def test_header_search_form_attr(driver, log_step):
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Kiểm tra xem có ô nhập liệu để tìm kiếm không")
    form = driver.find_element(By.NAME, "search-form")
    assert form.is_displayed()

@pytest.mark.tc(title="Header - Kiểm tra link Đăng nhập/Đăng xuất", priority="Medium")
def test_header_auth_links(driver, log_step):
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Tìm trên góc phải xem có link 'Login' hoặc 'Logout' không")
    links = driver.find_elements(By.TAG_NAME, "a")
    found = False
    for link in links:
        href = link.get_attribute("href")
        if href and ("login" in href or "logout" in href):
            found = True
            break
    assert found, "Không thấy link đăng nhập/xuất"

@pytest.mark.tc(title="Header - Kiểm tra icon Giỏ hàng", priority="High")
def test_header_cart_badge_structure(driver, log_step):
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Kiểm tra xem icon Giỏ hàng có hiển thị không")
    try:
        driver.find_element(By.PARTIAL_LINK_TEXT, "Gio")
    except:
        # Fallback
        assert len(driver.find_elements(By.CSS_SELECTOR, "a[href*='cart']")) > 0

# --- FOOTER ---

@pytest.mark.tc(title="Footer - Kiểm tra liên hệ", priority="High")
def test_footer_contact_info(driver, log_step):
    log_step("Bước 1: Kéo xuống cuối trang (Footer)")
    driver.get(BASE_URL)
    footer = driver.find_element(By.TAG_NAME, "footer")
    
    log_step("Bước 2: Đọc xem có Số điện thoại, Email và Địa chỉ không")
    txt = footer.text
    assert "0375217905" in txt
    assert "@" in txt
    assert "Hà Nội" in txt or "Chùa Bộc" in txt

@pytest.mark.tc(title="Footer - Kiểm tra logo đối tác", priority="Medium")
def test_footer_partner_images(driver, log_step):
    log_step("Bước 1: Kéo xuống cuối trang")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Quan sát xem có logo của VNPost hay GHN không")
    footer = driver.find_element(By.TAG_NAME, "footer")
    assert len(footer.find_elements(By.TAG_NAME, "img")) > 0

@pytest.mark.tc(title="Footer - Kiểm tra bản quyền", priority="Low")
def test_footer_copyright(driver, log_step):
    log_step("Bước 1: Vào trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Tìm dòng chữ bản quyền 'Bookworms Store' ở cuối cùng")
    assert "Bookworms Store" in driver.page_source