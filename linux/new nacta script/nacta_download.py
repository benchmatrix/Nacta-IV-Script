#!/usr/bin/env python3
import os
import time
import glob
import traceback
import smtplib
import schedule
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.cloud import storage

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'adminhost@benchmatrix.com',
    'sender_password': 'jdol ydge izik cmdq',
    'recipient_email': 'support.aml@benchmatrix.com',
    'subject_prefix': 'NACTA Download'
}

# Google Cloud Storage Configuration
GCS_CONFIG = {
    'bucket_name': 'nacta-bucket',
    'blob_name': 'NACTA.json',
}

# Download directory
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/home/opc/nacta')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Target file name
TARGET_FILE = "NACTA.JSON"
TARGET_FILE_PATH = os.path.join(DOWNLOAD_DIR, TARGET_FILE)

# Log file
LOG_FILE = os.path.join(DOWNLOAD_DIR, "nacta_download.log")

# Pakistan timezone
PAKISTAN_TZ = pytz.timezone('Asia/Karachi')


def log_message(message):
    """Log message to file and print to console"""
    timestamp = datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry.strip(), flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Could not write to log file: {e}")


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
                <h2>NACTA Download & GCS Upload {status}</h2>
            </div>
            <div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <h3>Details:</h3>
                <pre style="background-color: white; padding: 10px; border: 1px solid #ddd; border-radius: 3px; overflow-x: auto;">
{body}
                </pre>
            </div>
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>Timestamp (PKT): {datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>This is an automated notification from NACTA Download Service.</p>
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
        log_message(f"Failed to send email: {str(e)}")
        return False


def cleanup_old_files():
    """Remove old JSON files before download"""
    try:
        log_message("Cleaning up old local files...")
        
        if os.path.exists(TARGET_FILE_PATH):
            os.remove(TARGET_FILE_PATH)
            log_message(f"Removed existing file: {TARGET_FILE}")
        
        json_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.json"))
        files_removed = 0
        for json_file in json_files:
            try:
                os.remove(json_file)
                files_removed += 1
                log_message(f"Removed: {os.path.basename(json_file)}")
            except Exception as e:
                log_message(f"Could not remove {json_file}: {e}")
        
        log_message(f"Local cleanup completed. Removed {files_removed} file(s)")
        return True
        
    except Exception as e:
        log_message(f"Error during cleanup: {str(e)}")
        return False


def delete_old_gcs_file():
    """Delete the old NACTA file from GCS bucket"""
    try:
        log_message("Deleting old file from GCS bucket...")
        
        client = storage.Client()
        bucket = client.bucket(GCS_CONFIG['bucket_name'])
        blob = bucket.blob(GCS_CONFIG['blob_name'])
        
        if blob.exists():
            blob.delete()
            log_message(f"Deleted old file from GCS: {GCS_CONFIG['blob_name']}")
        else:
            log_message("No existing file found in GCS bucket")
        
        return True
        
    except Exception as e:
        log_message(f"Error deleting from GCS: {str(e)}")
        traceback.print_exc()
        return False


def upload_to_gcs(file_path):
    """Upload file to Google Cloud Storage bucket"""
    try:
        log_message("Uploading file to GCS bucket...")
        
        client = storage.Client()
        bucket = client.bucket(GCS_CONFIG['bucket_name'])
        blob = bucket.blob(GCS_CONFIG['blob_name'])
        
        blob.upload_from_filename(file_path, content_type='application/json')
        blob.make_public()
        
        public_url = blob.public_url
        file_size = os.path.getsize(file_path)
        
        log_message(f"File uploaded successfully to GCS")
        log_message(f"Public URL: {public_url}")
        log_message(f"File size: {file_size} bytes")
        
        return True, public_url
        
    except Exception as e:
        log_message(f"Error uploading to GCS: {str(e)}")
        traceback.print_exc()
        return False, None


def setup_chrome():
    """Setup Chrome driver for headless browsing"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.binary_location = "/usr/bin/chromium"

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)
    log_message("ChromeDriver setup successful!")
    return driver


def download_nacta_json():
    """Download NACTA JSON file from website"""
    driver = None
    download_success = False
    download_details = {
        'start_time': datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        'end_time': None,
        'file_size': 0,
        'file_path': None,
        'error': None,
        'cleanup_status': None,
        'gcs_delete_status': None,
        'gcs_upload_status': None,
        'gcs_url': None
    }
    
    try:
        # Step 1: Clean up old local files
        cleanup_success = cleanup_old_files()
        download_details['cleanup_status'] = "Success" if cleanup_success else "Failed"
        
        # Step 2: Delete old file from GCS
        gcs_delete_success = delete_old_gcs_file()
        download_details['gcs_delete_status'] = "Success" if gcs_delete_success else "Failed"
        
        log_message("Starting NACTA JSON download...")
        driver = setup_chrome()
        log_message("Opening NACTA website...")
        driver.get("https://nfs.nacta.gov.pk/")
        time.sleep(5)
        log_message(f"Page title: {driver.title}")

        log_message("Searching for JSON button...")
        wait = WebDriverWait(driver, 30)
        try:
            json_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='JSON']"))
            )
            log_message("JSON button found, clicking...")
            driver.execute_script("arguments[0].click();", json_button)
        except Exception as e:
            error_msg = f"JSON button not found: {str(e)}"
            log_message(error_msg)
            download_details['error'] = error_msg
            return False, download_details

        log_message("Waiting for download to complete...")
        timeout = 60
        elapsed = 0
        json_files = []
        
        while elapsed < timeout:
            json_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.json"))
            json_files = [f for f in json_files if not f.endswith('.crdownload')]
            if json_files:
                time.sleep(2)
                break
            time.sleep(1)
            elapsed += 1

        if json_files:
            latest_file = max(json_files, key=os.path.getctime)
            
            if latest_file != TARGET_FILE_PATH:
                os.rename(latest_file, TARGET_FILE_PATH)
                log_message(f"Renamed {os.path.basename(latest_file)} to {TARGET_FILE}")
            
            file_size = os.path.getsize(TARGET_FILE_PATH)
            
            if file_size == 0:
                error_msg = "Downloaded file is empty (0 bytes)"
                log_message(error_msg)
                download_details['error'] = error_msg
                return False, download_details
            
            log_message("DOWNLOAD SUCCESSFUL!")
            log_message(f"File: {TARGET_FILE_PATH}")
            log_message(f"Size: {file_size} bytes")
            
            # Step 3: Upload to GCS
            upload_success, gcs_url = upload_to_gcs(TARGET_FILE_PATH)
            
            download_success = upload_success
            download_details.update({
                'end_time': datetime.now(PAKISTAN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                'file_size': file_size,
                'file_path': TARGET_FILE_PATH,
                'gcs_upload_status': "Success" if upload_success else "Failed",
                'gcs_url': gcs_url
            })
            
            if not upload_success:
                download_details['error'] = "File downloaded but GCS upload failed"
                
        else:
            error_msg = f"No JSON file found after {timeout} seconds. Available files: {os.listdir(DOWNLOAD_DIR)}"
            log_message(error_msg)
            download_details['error'] = error_msg

    except Exception as e:
        error_msg = str(e)
        log_message(f"ERROR: {error_msg}")
        traceback.print_exc()
        download_details['error'] = error_msg
    finally:
        if driver:
            driver.quit()
            log_message("Browser closed")
    
    return download_success, download_details


def run_daily_job():
    """Main job to run daily"""
    log_message("=" * 50)
    log_message("Starting NACTA Download & GCS Upload Job")
    log_message(f"Current time (PKT): {datetime.now(PAKISTAN_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("=" * 50)
    
    success, details = download_nacta_json()
    
    if success:
        subject = "Download & Upload Completed Successfully"
        body = f"""
Download & Upload Status: SUCCESS

Timing:
  Start Time (PKT): {details['start_time']}
  End Time (PKT): {details['end_time']}

Local File:
  Path: {details['file_path']}
  Size: {details['file_size']} bytes

GCS Upload:
  Bucket: {GCS_CONFIG['bucket_name']}
  Blob Name: {GCS_CONFIG['blob_name']}
  Upload Status: {details['gcs_upload_status']}
  Public URL: {details['gcs_url']}

Cleanup:
  Local Cleanup: {details['cleanup_status']}
  GCS Old File Delete: {details['gcs_delete_status']}
        """
    else:
        subject = "Download/Upload Failed"
        body = f"""
Download/Upload Status: FAILED

Start Time (PKT): {details['start_time']}

Status:
  Local Cleanup: {details.get('cleanup_status', 'Not attempted')}
  GCS Delete Old: {details.get('gcs_delete_status', 'Not attempted')}
  GCS Upload: {details.get('gcs_upload_status', 'Not attempted')}

Error: {details['error']}

Please check the container logs for more details:
  docker logs nacta_downloader
        """
    
    log_message("Sending email notification...")
    send_email(subject, body, success)
    
    log_message("=" * 50)
    log_message("Job completed")
    log_message("=" * 50 + "\n")


def main():
    """Main function with scheduling"""
    log_message("=" * 50)
    log_message("NACTA Download Service Started (Docker)")
    log_message(f"Current time (PKT): {datetime.now(PAKISTAN_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Download directory: {DOWNLOAD_DIR}")
    log_message(f"GCS Bucket: {GCS_CONFIG['bucket_name']}")
    log_message("Scheduled to run daily at 14:00 PKT")
    log_message("=" * 50)
    
    # Verify GCS credentials
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path and os.path.exists(creds_path):
        log_message(f"GCS credentials found at: {creds_path}")
    else:
        log_message("WARNING: GCS credentials not found!")
    
    # Run immediately on startup
    log_message("Running initial job on startup...")
    run_daily_job()
    
    # Schedule daily at 2 PM Pakistan time
    schedule.every().day.at("14:00").do(run_daily_job)
    
    log_message(f"Next scheduled run: {schedule.next_run()}")
    log_message("Scheduler running. Waiting for next scheduled time...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
