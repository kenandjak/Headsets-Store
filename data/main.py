import os
import time
import re
import psycopg2
from dotenv import load_dotenv
from ultralytics import YOLO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from PIL import Image

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

MODEL_PATH = "weights/best.pt"
model = YOLO(MODEL_PATH)

opt = Options()
opt.add_argument("-private")
opt.set_preference("browser.privatebrowsing.autostart", True)
opt.add_argument("--width=1280")
opt.add_argument("--height=700")

browser = webdriver.Firefox(options=opt)
products_seen = set()

def connect_database():
    db_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(db_url)

def send_to_postgres(description, price, link):
    try:
        conn = connect_database()
        cur = conn.cursor()
        query = """
            INSERT INTO headsets_store (description, price, link)
            VALUES (%s, %s, %s)
            ON CONFLICT (link) DO NOTHING;
        """
        cur.execute(query, (description, price, link))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error saving to database.: {e}")

def remove_popups():
    script = """
    const selectors = ['#credential_picker_container', '.nav-header-plus-cp-container', 'iframe[src*="accounts.google.com"]', '.nav-cookie-disclaimer'];
    selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
    const header = document.querySelector('header');
    if(header) header.style.position = 'absolute'; 
    """
    browser.execute_script(script)

def pricing_treatment(price_text):
    if not price_text: return 0
    text = price_text.replace('.', '').split(',')[0].replace('\n', ' ')
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else 0

def extraction(page_number):
    temp_img = "temp_capture.png"
    browser.save_screenshot(temp_img)
    
    with Image.open(temp_img) as img:
        img_w, _ = img.size
    win_w = browser.execute_script("return window.innerWidth;")
    scale_factor = img_w / win_w 
    
    results = model.predict(source=temp_img, conf=0.35, imgsz=1024, verbose=False)
    detections = results[0].boxes
    
    if len(detections) == 0: return

    objs = []
    for box in detections:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        objs.append({
            'label': model.names[int(box.cls[0])],
            'center_css': (int(((x1+x2)/2) / scale_factor), int(((y1+y2)/2) / scale_factor))
        })

    cards = browser.find_elements(By.CSS_SELECTOR, ".poly-card, .ui-search-layout__item")
    
    for card in cards:
        rect = browser.execute_script("return arguments[0].getBoundingClientRect();", card)
        x_min, x_max, y_min, y_max = rect['left'], rect['right'], rect['top'], rect['bottom']
        
        desc_text, price_int, link_product = "", 0, ""
        headset_image_detected = False 
        
        for obj in objs:
            cx, cy = obj['center_css']
            if x_min <= cx <= x_max and y_min <= cy <= y_max:
                if obj['label'] == 'headset': headset_image_detected = True
                if obj['label'] == 'description':
                    try:
                        link_el = card.find_element(By.CSS_SELECTOR, "a[class*='title'], h2 a")
                        desc_text = link_el.text.split('\n')[0].strip()
                        link_product = link_el.get_attribute("href")
                    except: continue
                if obj['label'] == 'price':
                    try:
                        p_el = card.find_element(By.CSS_SELECTOR, "[class*='price__current']")
                        price_int = pricing_treatment(p_el.text)
                    except: continue

        if headset_image_detected and desc_text and price_int > 0:
            if link_product not in products_seen:
                print(f"HEADSET DETECTED: {desc_text[:50]}...")
                print(f"   Price: R$ {price_int}")
                
                send_to_postgres(desc_text, price_int, link_product)
                
                products_seen.add(link_product)

try:
    browser.get('https://lista.mercadolivre.com.br/headset')
    time.sleep(5)
    for p in range(1, 6):
        remove_popups()
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        elements = browser.find_elements(By.CSS_SELECTOR, ".poly-card, .ui-search-layout__item")
        positions_y = sorted(list(set([int(e.location['y']) for e in elements])))

        print(f"\n--- Processing Page {p} ---")
        for y in positions_y:
            if y > (positions_y[-1] - 50): continue
            browser.execute_script(f"window.scrollTo(0, {y - 40});")
            time.sleep(1.2)
            remove_popups()
            extraction(p)

        try:
            btn = browser.find_element(By.CSS_SELECTOR, 'li.andes-pagination__button--next a')
            browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(1.5)
            btn.click()
            time.sleep(4)
        except: break
finally:
    browser.quit()
    print(f"\nEnd of Collection: {len(products_seen)}")