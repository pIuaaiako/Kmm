import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init

# ตั้งค่าสีและอีโมจิ
init(autoreset=True)
c_user = Fore.CYAN
c_pass = Fore.MAGENTA
c_money = Fore.GREEN
c_wallet = Fore.YELLOW
c_point = Fore.BLUE
c_err = Fore.RED
c_reset = Style.RESET_ALL

print(f"""
{Fore.YELLOW}╔══════════════════════════════════════════════════════════╗
║  🚀  {Fore.CYAN}BYSHOP AUTO CHECKER {Fore.YELLOW}- {Fore.GREEN}ยอดเงิน & WALLET & แต้ม  {Fore.YELLOW}🚀  ║
║  📂  {Fore.WHITE}Load: msd.txt   {Fore.YELLOW}|   💾 {Fore.WHITE}Save: Ex_account.txt        ║
╚══════════════════════════════════════════════════════════╝{c_reset}
""")

# ฟังก์ชันบันทึกไฟล์ทันที
def save_data(username, password, money, wallet, point):
    with open("Ex_account.txt", "a", encoding="utf-8") as f:
        f.write(f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        f.write(f"👤 ชื่อ      : {username}\n")
        f.write(f"🔑 รหัสผ่าน  : {password}\n")
        f.write(f"💰 ยอดเงิน   : {money}\n")
        f.write(f"💳 Wallet    : {wallet}\n")
        f.write(f"🏆 แต้มสะสม  : {point}\n")
        f.write(f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

# ตั้งค่า Browser
options = webdriver.ChromeOptions()
options.add_argument("--mute-audio")
# options.add_argument("--headless") # เปิดบรรทัดนี้ถ้าไม่อยากเห็นหน้าต่าง Chrome
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # โหลดไฟล์ msd.txt
    with open("msd.txt", "r", encoding="utf-8") as f:
        accounts = [line.strip() for line in f if line.strip()]

    print(f"{Fore.YELLOW}⚡ พบทั้งหมด {len(accounts)} บัญชี... เริ่มกันเลย!{c_reset}\n")

    for i, account in enumerate(accounts):
        if ":" in account:
            user, pwd = account.split(":", 1)
        else:
            print(f"{c_err}❌ รูปแบบไอดีผิด (ต้องเป็น user:pass): {account}{c_reset}")
            continue

        try:
            driver.get("https://byshop.me/buy/")
            
            # รอช่องกรอก Username และใส่ข้อมูล
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(user)
            driver.find_element(By.ID, "password").send_keys(pwd)
            
            print(f"{Fore.WHITE}🔄 กำลังล็อกอิน: {c_user}{user}{c_reset} ... (รอกดยืนยัน/Captcha ถ้ามี)")

            # คลิกปุ่มเข้าสู่ระบบ (รหัสปุ่ม btn)
            try:
                login_btn = driver.find_element(By.ID, "btn")
                driver.execute_script("arguments[0].click();", login_btn)
            except:
                pass

            # ⏳ จุดสำคัญ: รอให้ล็อกอินผ่าน โดยเช็คจาก Element "ยอดเงิน" (navbarDropdown) ที่จะโผล่มาหลังเข้าได้เท่านั้น 
            # ตรงนี้จะรอ Cloudflare/Captcha ให้เสร็จไปในตัว สูงสุด 30 วินาที
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "navbarDropdown"))
                )
            except:
                print(f"{c_err}❌ ล็อกอินไม่สำเร็จ หรือ ติด Captcha นานเกินไป: {user}{c_reset}")
                continue

            # ✅ ดึงข้อมูล (Scraping)
            # ดึงยอดเงินจาก Navbar
            money_text = driver.find_element(By.ID, "navbarDropdown").text
            money = money_text.replace("ยอดเงิน:", "").replace("บาท", "").strip()

            # เพื่อความชัวร์ ดึง Wallet และ แต้ม จาก Dropdown (ต้องหา element ที่ซ่อนอยู่)
            # ใช้ get_attribute("innerText") เพื่อดึงข้อความแม้ element จะไม่ถูกคลิกโชว์
            page_source = driver.page_source
            
            # ใช้ Logic ง่ายๆ หา Text จาก HTML เพราะ Element ซ้อนกัน [cite: 10, 11]
            wallet = "0.00"
            point = "0"
            
            # ค้นหา Wallet และ แต้ม แบบเจาะจง
            all_items = driver.find_elements(By.CLASS_NAME, "dropdown-item")
            for item in all_items:
                txt = item.get_attribute("innerText")
                if "Wallet" in txt:
                    wallet = txt.split(":")[-1].replace("บาท", "").strip() # 
                if "แต้มสะสม" in txt:
                    point = txt.split(":")[-1].replace("แต้ม", "").strip() # 

            # 💾 บันทึกทันที
            save_data(user, pwd, money, wallet, point)

            # 🎨 แสดงผลสวยๆ
            print(f"   {Fore.GREEN}✅ เข้าสู่ระบบสำเร็จ!{c_reset}")
            print(f"   ├─ 💰 ยอดเงิน  : {c_money}{money} บาท{c_reset}")
            print(f"   ├─ 💳 Wallet   : {c_wallet}{wallet} บาท{c_reset}")
            print(f"   └─ 🏆 แต้มสะสม : {c_point}{point} แต้ม{c_reset}")
            print(f"{Fore.DARK_GREY}----------------------------------------{c_reset}")

            # ล้าง Cookies เตรียมไอดีต่อไป
            driver.delete_all_cookies()

        except Exception as e:
            print(f"{c_err}⚠️ เกิดข้อผิดพลาดกับ {user}: {str(e)}{c_reset}")
            driver.delete_all_cookies()

except FileNotFoundError:
    print(f"{c_err}❌ ไม่พบไฟล์ msd.txt กรุณาสร้างไฟล์ก่อน{c_reset}")
except KeyboardInterrupt:
    print(f"\n{Fore.YELLOW}🛑 หยุดการทำงานแล้ว{c_reset}")
finally:
    driver.quit()
    print(f"\n{Fore.GREEN}✅ เสร็จสิ้น! ข้อมูลถูกบันทึกใน Ex_account.txt{c_reset}")