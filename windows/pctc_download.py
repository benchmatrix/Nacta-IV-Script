#!/usr/bin/env python3
"""
PCTC Download Script for Windows Server
Run as Windows Service with NSSM
"""
import os
import time
import glob
import traceback
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# CONFIGURATION
# ============================================================

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'adminhost@benchmatrix.com',
    'sender_password': 'jdol ydge izik cmdq',
    'recipient_email': 'amir.khan@benchmatrix.com',
    'subject_prefix': 'PCTC Download'
}

# Website Configuration
WEBSITE_CONFIG = {
    'main_url': 'https://pctc.pss.gov.sa/wps/portal/departments/pcct/sl/!ut/p/z1/jZDLCsIwEEW_pV8wk2kc67IE2_QBamJozUayKgWtIuL3K3Vt7OwGzrnDXPDQg5_CaxzCc7xN4fLZT57PTK0SOqMms46Q621T1bpAJIJuBoTelFpJsSuLY4oHJivStUHUBH6Jj5WUWkhqcGUU5syulGxQtmKh_2NyXOZHAB-P78DPSKyBb0bkxX9HbHjA_eqc63HcD0nyBizU2GM!/dz/d5/L0lHSkovd0RNQUZrQUVnQSEhLzROVkUvZW4!/',
}

# Fixed base directory on C: drive
BASE_DIR = r'C:\PCTC'

# Directory paths
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# ChromeDriver path (place chromedriver.exe in C:\PCTC)
CHROME_DRIVER_PATH = os.path.join(BASE_DIR, 'chromedriver.exe')

# Create directories if they don't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Target file name
TARGET_FILE = "PCTC.JSON"
TARGET_FILE_PATH = os.path.join(DOWNLOAD_DIR, TARGET_FILE)

# Log files
LOG_FILE = os.path.join(LOGS_DIR, "pctc_download.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "pctc_error.log")

# Pakistan timezone
PAKISTAN_TZ = pytz.timezone('Asia/Karachi')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)

# ============================================================
# FUNCTIONS
# ============================================================

def log_message(message, level='info'):
    """Log message to file and console"""
    timestamp = datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if level == 'error':
        logging.error(log_entry)
    elif level == 'warning':
        logging.warning(log_entry)
    else:
        logging.info(log_entry)
    
    # Also write to error log if it's an error
    if level == 'error':
        try:
            with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry}\n")
        except:
            pass


def send_email(subject, body, is_success=True):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = f"{EMAIL_CONFIG['subject_prefix']} - {subject}"
        
        color = "#28a745" if is_success else "#dc3545"
        status = "SUCCESS" if is_success else "FAILED"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {color}; color: white; padding: 10px; border-radius: 5px;">
                <h2>PCTC Download {status}</h2>
            </div>
            <div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <h3>Details:</h3>
                <pre style="background-color: white; padding: 10px; border: 1px solid #ddd; border-radius: 3px; overflow-x: auto;">
{body}
                </pre>
            </div>
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>Timestamp (PKT): {datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>Server: Windows Server</p>
                <p>This is an automated notification from PCTC Download Service.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        log_message(f"Email sent successfully to {EMAIL_CONFIG['recipient_email']}")
        return True
        
    except Exception as e:
        log_message(f"Failed to send email: {str(e)}", 'error')
        return False


def cleanup_old_files():
    """Remove old files before download"""
    try:
        log_message("Cleaning up old local files...")
        
        if os.path.exists(TARGET_FILE_PATH):
            os.remove(TARGET_FILE_PATH)
            log_message(f"Removed existing file: {TARGET_FILE}")
        
        # Clean up old downloaded files (keep only last 5)
        all_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.*"))
        files_removed = 0
        
        # Sort by creation time
        all_files.sort(key=os.path.getctime)
        
        # Keep only last 5 files, remove rest
        for file in all_files[:-5]:
            if file.endswith('.log') or file.endswith('.py'):
                continue
            try:
                os.remove(file)
                files_removed += 1
                log_message(f"Removed old file: {os.path.basename(file)}")
            except Exception as e:
                log_message(f"Could not remove {file}: {e}", 'warning')
        
        log_message(f"Local cleanup completed. Removed {files_removed} old file(s)")
        return True
        
    except Exception as e:
        log_message(f"Error during cleanup: {str(e)}", 'error')
        return False


def setup_chrome():
    """Setup Chrome driver for Windows Server using local chromedriver"""
    try:
        chrome_options = Options()
        
        # Headless mode for Windows Server (no GUI)
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--log-level=3")  # Suppress logging
        chrome_options.add_argument("--silent")

        # FIX FOR ERR_CONNECTION_RESET - Add these options
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-insecure-localhost")
        
        # Download settings
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # MODIFIED: Use webdriver-manager for automatic ChromeDriver management
        try:
            log_message("Using webdriver-manager to automatically handle ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            log_message("✓ ChromeDriver automatically configured with matching version")
        except ImportError:
            log_message("webdriver-manager not installed, falling back to local ChromeDriver...", 'warning')
             # Fallback to local chromedriver (legacy)
            if os.path.exists(CHROME_DRIVER_PATH):
                log_message(f"Using local ChromeDriver at: {CHROME_DRIVER_PATH}")
                service = Service(CHROME_DRIVER_PATH)
            elif os.path.exists("chromedriver.exe"):
                log_message("Using ChromeDriver from current directory")
                service = Service("chromedriver.exe")
            else:
                log_message("No ChromeDriver found. Please install: pip install webdriver-manager", 'error')
                raise Exception("ChromeDriver not found")
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        log_message("ChromeDriver setup successful on Windows Server!")
        return driver
        
    except Exception as e:
        log_message(f"Failed to setup Chrome: {str(e)}", 'error')
        log_message("Please ensure webdriver-manager is installed: pip install webdriver-manager", 'error')
        raise

def test_connectivity():
    """Test if PCTC portal is accessible"""
    try:
        import requests
        log_message("Testing connectivity to PCTC portal...")
        response = requests.get(
            WEBSITE_CONFIG['main_url'],
            timeout=15,
            verify=False,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        if response.status_code == 200:
            log_message("✓ PCTC portal is accessible")
            return True
        else:
            log_message(f"✗ Portal returned HTTP {response.status_code}", 'warning')
            return False
    except Exception as e:
        log_message(f"✗ Cannot access PCTC portal: {str(e)}", 'warning')
        log_message("Note: This script may need to run from within KSA network", 'warning')
        return False


def download_pctc_file():
    """Main download function"""
    driver = None
    download_success = False
    start_time = datetime.now(PAKISTAN_TZ)
    
    download_details = {
        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'end_time': None,
        'file_size': 0,
        'file_path': None,
        'error': None,
        'cleanup_status': None
    }
    
    try:
        log_message("=" * 60)
        log_message("PCTC DOWNLOAD JOB STARTED")
        log_message(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_message(f"Download Directory: {DOWNLOAD_DIR}")
        log_message("=" * 60)
        
        # Test connectivity first
        test_connectivity()
        
        # Clean up old files
        cleanup_success = cleanup_old_files()
        download_details['cleanup_status'] = "Success" if cleanup_success else "Failed"
        
        # Setup Chrome and download
        log_message("Initializing Chrome browser...")
        driver = setup_chrome()
        
        log_message(f"Opening PCTC portal...")
        driver.get(WEBSITE_CONFIG['main_url'])
        time.sleep(15)  # Wait for page load
        log_message(f"Page title: {driver.title}")
        
        # Find and click download button
        log_message("Searching for download button...")
        wait = WebDriverWait(driver, 45)
        
        # Try multiple button text options
        download_button = None
        # button_texts = ['Download', 'تحميل']
        

        # Method 1: Look for the exact "Download" button (from your screenshot)
        try:
            # Wait for the button to be present (it might be inside a div or table)
            download_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
            )
            log_message("✓ Found Download button by text")
        except:
            pass

        # Method 2: Look for the button in the same structure as your screenshot
        if not download_button:
            try:
                # Look for button that contains "Download" text
                download_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]"))
                )
                log_message("✓ Found Download button by button tag")
            except:
                pass

        # Method 3: Look for download links within the sanction list area
        if not download_button:
            try:
                # Look for any element with "Download" text that's a link or button
                download_button = wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Download"))
                )
                log_message("✓ Found Download button by link text")
            except:
                pass

        # Method 4: Look for Download text in the specific context of National Terrorism List
        if not download_button:
            try:
                # Look for the section containing "National Terrorism List (1373)" then find Download nearby
                download_button = driver.find_element(
                    By.XPATH, "//*[contains(text(), 'National Terrorism List')]/following::*[contains(text(), 'Download')][1]"
                )
                if download_button and download_button.is_displayed():
                    log_message("✓ Found Download button near National Terrorism List text")
            except:
                pass
        
        # Method 5: Look for any clickable element with Download text (more flexible)
        if not download_button:
            try:
                elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Download')]")
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        download_button = elem
                        log_message("✓ Found clickable Download element")
                        break
            except:
                pass

        if not download_button:
            error_msg = "Download button not found on the page"
            log_message(error_msg, 'error')
            download_details['error'] = error_msg

            try:
                debug_file = os.path.join(LOGS_DIR, "page_source_no_button.html")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                log_message(f"Page source saved to: {debug_file}")
                
                # Take screenshot
                screenshot_file = os.path.join(LOGS_DIR, "no_button_screenshot.png")
                driver.save_screenshot(screenshot_file)
                log_message(f"Screenshot saved to: {screenshot_file}")
            except Exception as debug_e:
                log_message(f"Debug save failed: {debug_e}")
            
            return False, download_details
        
        # for button_text in button_texts:
        #     try:
        #         download_button = wait.until(
        #             EC.element_to_be_clickable((By.XPATH, f"//*[text()='{button_text}']"))
        #         )
        #         log_message(f"✓ Found button with text: {button_text}")
        #         break
        #     except:
        #         continue
        
        # # Try by partial text if not found
        # if not download_button:
        #     try:
        #         download_button = wait.until(
        #             EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Down"))
        #         )
        #         log_message("✓ Found button with partial text")
        #     except:
        #         pass
        
        # if not download_button:
        #     error_msg = "Download button not found on the page"
        #     log_message(error_msg, 'error')
        #     download_details['error'] = error_msg
        #     return False, download_details
        
        # Click the button
        log_message("Clicking download button...")
        driver.execute_script("arguments[0].click();", download_button)
        log_message("Download button clicked successfully")
        
        # Wait for download
        log_message("Waiting for download to complete...")
        timeout = 180  # 3 minutes timeout
        elapsed = 0
        downloaded_files = []
        
        while elapsed < timeout:
            # Check for any downloaded files
            downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.*"))
            downloaded_files = [f for f in downloaded_files 
                              if not f.endswith('.crdownload') 
                              and not f.endswith('.tmp')
                              and f != TARGET_FILE_PATH
                              and not f.endswith('.log')]
            
            if downloaded_files:
                log_message(f"Found {len(downloaded_files)} downloaded file(s)")
                time.sleep(3)  # Extra wait to ensure download is complete
                break
                
            time.sleep(2)
            elapsed += 2
            
            if elapsed % 20 == 0:
                log_message(f"Still waiting... {elapsed}/{timeout} seconds")
        
        # Process downloaded file
        if downloaded_files:
            # Get the latest file
            latest_file = max(downloaded_files, key=os.path.getctime)
            file_size = os.path.getsize(latest_file)
            file_ext = os.path.splitext(latest_file)[1].lower()
            
            log_message(f"Downloaded file: {os.path.basename(latest_file)}")
            log_message(f"File size: {file_size:,} bytes")
            log_message(f"File type: {file_ext}")
            
            # Rename to PCTC.JSON
            if latest_file != TARGET_FILE_PATH:
                if os.path.exists(TARGET_FILE_PATH):
                    os.remove(TARGET_FILE_PATH)
                os.rename(latest_file, TARGET_FILE_PATH)
                log_message(f"Renamed to {TARGET_FILE}")
            
            if file_size == 0:
                error_msg = "Downloaded file is empty (0 bytes)"
                log_message(error_msg, 'error')
                download_details['error'] = error_msg
                return False, download_details
            
            download_success = True
            download_details.update({
                'end_time': datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                'file_size': file_size,
                'file_path': TARGET_FILE_PATH
            })
            
            log_message("✅ DOWNLOAD SUCCESSFUL!")
            log_message(f"File saved to: {TARGET_FILE_PATH}")
            
        else:
            error_msg = f"No file downloaded after {timeout} seconds"
            log_message(error_msg, 'error')
            download_details['error'] = error_msg
            
            # List directory contents for debugging
            dir_contents = os.listdir(DOWNLOAD_DIR)
            log_message(f"Directory contents: {dir_contents}", 'warning')
            
    except Exception as e:
        error_msg = str(e)
        log_message(f"ERROR: {error_msg}", 'error')
        traceback.print_exc(file=open(ERROR_LOG_FILE, 'a'))
        download_details['error'] = error_msg
        
    finally:
        if driver:
            driver.quit()
            log_message("Browser closed")
        
        end_time = datetime.now(PAKISTAN_TZ)
        duration = (end_time - start_time).total_seconds()
        log_message(f"Total execution time: {duration:.2f} seconds")
        log_message("=" * 60)
    
    return download_success, download_details


def run_once():
    """Run the download job once (for scheduled tasks)"""
    log_message("PCTC Service - Starting one-time download")
    success, details = download_pctc_file()
    
    # Send email notification
    if success:
        subject = "Download Completed Successfully"
        body = f"""
Download Status: SUCCESS

Start Time: {details['start_time']}
End Time: {details['end_time']}

File Details:
  Path: {details['file_path']}
  Size: {details['file_size']:,} bytes

Cleanup Status: {details['cleanup_status']}

File saved to: {details['file_path']}
        """
    else:
        subject = "Download Failed"
        body = f"""
Download Status: FAILED

Start Time: {details['start_time']}

Status:
  Cleanup: {details.get('cleanup_status', 'Not attempted')}

Error: {details['error']}

Please check logs at: {LOG_FILE}
        """
    
    send_email(subject, body, success)
    
    # Return exit code for service monitoring
    return 0 if success else 1


def run_service():
    """Run as Windows service - continuous mode"""
    log_message("PCTC Service started in continuous mode")
    log_message(f"Download directory: {DOWNLOAD_DIR}")
    log_message(f"Logs directory: {LOGS_DIR}")
    
    # Run once on startup
    run_once()
    
    # For service mode, we exit after one run
    # Windows Task Scheduler will trigger the service daily
    log_message("Service execution completed. Exiting.")


if __name__ == "__main__":
    # Check if running as service or command line
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--service':
        run_service()
    else:
        # Run once (for testing or scheduled tasks)
        exit_code = run_once()
        sys.exit(exit_code)