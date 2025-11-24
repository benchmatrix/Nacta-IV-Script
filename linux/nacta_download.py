#!/usr/bin/env python3
import os
import time
import glob
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# For serving the file
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Download directory inside Docker container
DOWNLOAD_DIR = "/home/opc/nacta"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def setup_chrome():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Enable headless downloads
    chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Use correct path for chromedriver
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ ChromeDriver setup successful!")
    return driver

def download_nacta_json():
    driver = None
    try:
        print("🚀 Starting NACTA JSON download...")
        driver = setup_chrome()
        print("🌐 Opening NACTA website...")
        driver.get("https://nfs.nacta.gov.pk/")
        time.sleep(5)
        print(f"📄 Page title: {driver.title}")

        print("🔍 Searching for JSON button...")
        wait = WebDriverWait(driver, 30)
        try:
            json_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='JSON']"))
            )
            print("✅ JSON button found, clicking...")
            driver.execute_script("arguments[0].click();", json_button)
        except:
            print("💥 ERROR: JSON button not found!")
            return False

        print("⏬ Waiting for download to complete...")
        # Poll the download directory for the JSON file
        timeout = 30  # seconds
        elapsed = 0
        json_files = []
        while elapsed < timeout:
            json_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.json"))
            if json_files:
                break
            time.sleep(1)
            elapsed += 1

        if json_files:
            old_file = json_files[0]
            new_file = os.path.join(DOWNLOAD_DIR, "NACTA.JSON")
            if os.path.exists(new_file):
                os.remove(new_file)
            os.rename(old_file, new_file)
            file_size = os.path.getsize(new_file)
            print(f"🎉 DOWNLOAD SUCCESSFUL!")
            print(f"📁 File: {new_file}")
            print(f"📊 Size: {file_size} bytes")
            return True
        else:
            print(f"❌ No JSON file found. Available files: {os.listdir(DOWNLOAD_DIR)}")
            return False

    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()
            print("🔚 Browser closed")

# ------------------------------
# HTTP server to serve the JSON file
# ------------------------------
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/nacta/Nacta.json": 
            self.path = "/NACTA.JSON"
            # Add this header to force download
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", "attachment; filename=NACTA.JSON")
            self.end_headers()
            with open(self.path[1:], "rb") as f:  # remove leading '/'
                self.wfile.write(f.read())
        else:
            return super().do_GET()


def serve_file():
    os.chdir(DOWNLOAD_DIR)
    server_address = ("0.0.0.0", 5002)
    httpd = HTTPServer(server_address, Handler)
    print("🚀 Serving NACTA.JSON at http://0.0.0.0:5002/nacta/")
    httpd.serve_forever()


# ------------------------------
# Main execution
# ------------------------------
if __name__ == "__main__":
    download_nacta_json()  # attempt, but server runs regardless

    print("\n" + "="*50)
    print("📡 Starting HTTP server on port 5002 (download success not required)")
    print("="*50)

    serve_file()  # ALWAYS start the HTTP server

