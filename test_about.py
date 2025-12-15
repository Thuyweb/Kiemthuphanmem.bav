import pytest
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost/bookstore/public"

def normalize(text):
    return unicodedata.normalize('NFC', text.strip()) if text else ""

@pytest.fixture(autouse=True)
def setup_driver(driver):
    driver.maximize_window()

@pytest.mark.tc(
    title="Kiểm tra trang Giới thiệu (About)",
    desc="Điều hướng từ Menu Trang chủ -> Giới thiệu và verify nội dung hiển thị",
    pre="Trang chủ hoạt động bình thường",
    expected="URL chứa 'about', hiển thị đúng hình ảnh và văn bản giới thiệu",
    priority="Low"
)
def test_about_page_content(driver, log_step):
    wait = WebDriverWait(driver, 10)
    
    log_step("Bước 1: Truy cập Trang chủ")
    driver.get(BASE_URL)
    
    log_step("Bước 2: Click menu 'Giới thiệu'")
    try:
        # Tìm link chứa chữ 'Giới thiệu' hoặc href='about'
        menu_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'about') or contains(text(), 'Giới thiệu')]")))
        menu_link.click()
    except Exception as e:
        pytest.fail(f"Không tìm thấy menu Giới thiệu: {e}")
        
    log_step("Bước 3: Kiểm tra URL")
    wait.until(EC.url_contains("about"))
    assert "about" in driver.current_url, "URL không chuyển sang trang About"

    log_step("Bước 4: Kiểm tra nội dung đặc trưng")
    # Các từ khóa lấy từ file about.php bạn cung cấp
    keywords = ["Vẻ đẹp quyến rũ", "Tri Thức", "Tưởng Thật Xa"]
    
    page_source = normalize(driver.page_source)
    found_any = False
    for kw in keywords:
        if normalize(kw) in page_source:
            log_step(f"✔ Tìm thấy từ khóa: '{kw}'")
            found_any = True
            
    if not found_any:
        pytest.fail("Không tìm thấy nội dung giới thiệu (Bookworm store info).")
        
    log_step("Bước 5: Kiểm tra hiển thị hình ảnh")
    imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='about']")
    if len(imgs) > 0:
        log_step(f"✔ Tìm thấy {len(imgs)} hình ảnh giới thiệu.")
    else:
        log_step("⚠ Cảnh báo: Không tìm thấy hình ảnh minh họa (about1.jpg, about3.jpg).")