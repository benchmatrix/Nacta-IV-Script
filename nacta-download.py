import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

# === Set fixed paths ===
download_dir = "C:\inetpub\wwwroot\Sanction"
log_dir = "C:\inetpub\wwwroot\Sanction"
os.makedirs(log_dir, exist_ok=True)

# === Setup logging ===
log_file = os.path.join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.txt")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === Chrome options for silent download ===
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

try:
    logging.info("Launching browser...")
    driver_path = ChromeDriverManager().install()
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    logging.info("Opening NACTA website...")
    driver.get("https://nfs.nacta.gov.pk/")
    time.sleep(60)

    logging.info("Finding JSON download button...")
    download_button = driver.find_element(By.XPATH, "//button[text()='JSON']")
    driver.execute_script("arguments[0].click();", download_button)

    logging.info("Waiting for file to be downloaded (3 minutes)...")
    time.sleep(60)  # Wait 3 minutes

    # Wait for any .crdownload to finish
    for _ in range(30):  # Check every 2 sec for max 1 minute
        if any(f.endswith(".crdownload") for f in os.listdir(download_dir)):
            time.sleep(2)
        else:
            break

    logging.info("Scanning downloaded files...")
    files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith(".json")]
    if not files:
        raise Exception("No .json file found in download directory.")

    latest_file = max(files, key=os.path.getmtime)
    nacta_file_path = os.path.join(download_dir, "NACTA.json")

    if os.path.exists(nacta_file_path):
        logging.info("Deleting old NACTA.json file...")
        os.remove(nacta_file_path)

    os.rename(latest_file, nacta_file_path)
    logging.info(f"File renamed to: {nacta_file_path}")
    logging.info("Download and rename completed successfully.")

except Exception as e:
    logging.error(f"An error occurred: {str(e)}")

finally:
    logging.info("Closing browser.")
    driver.quit()
