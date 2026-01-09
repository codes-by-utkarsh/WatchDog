import os
import time
import json
import cv2
import requests
import win32evtlog
import threading

# --------------------------------------------------
# PATHS (SERVICE SAFE)
# --------------------------------------------------
import sys

if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    BASE_DIR = os.path.dirname(sys.executable)
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    # Running as Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(BASE_DIR)
    CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")

IMAGE_DIR = os.getenv("PROGRAMDATA") or "C:\\ProgramData"
CAPTURES_DIR = os.path.join(IMAGE_DIR, "AntiTheftCaptures")
if not os.path.exists(CAPTURES_DIR):
    try:
        os.makedirs(CAPTURES_DIR)
    except Exception as e:
        print(f"[ERROR] Could not create capture dir: {e}")

CAPTURE_COOLDOWN = 1  # seconds (no more photos within this time)
last_capture_time = 0


# --------------------------------------------------
# LOAD CONFIG (SAFE)
# --------------------------------------------------
def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

CONFIG = load_config()

# Telegram
BOT_TOKEN = CONFIG.get("telegram", {}).get("bot_token")
CHAT_ID = CONFIG.get("telegram", {}).get("chat_id")

# Security
FAILED_THRESHOLD = CONFIG.get("security", {}).get("failed_attempt_threshold", 2)
TARGET_EVENT_ID = CONFIG.get("security", {}).get("event_id", 4625)
CHECK_INTERVAL = CONFIG.get("security", {}).get("check_interval_seconds", 0.1)

# Camera
CAM_INDEX = CONFIG.get("camera", {}).get("device_index", 0)

# --------------------------------------------------
# TELEGRAM
# --------------------------------------------------
# --------------------------------------------------
# UPLOAD WORKER (QUEUE HANDLER)
# --------------------------------------------------
def check_internet():
    try:
        requests.get("https://www.google.com", timeout=1)
        return True
    except:
        return False

def send_telegram_photo(image_path):
    if not BOT_TOKEN or not CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id": CHAT_ID,
        "caption": "🚨 Wrong PIN attempt detected! (Buffered Image)"
    }

    try:
        with open(image_path, "rb") as img:
            files = {"photo": img}
            resp = requests.post(url, data=data, files=files, timeout=20)
            return resp.status_code == 200
    except Exception as e:
        print(f"[DEBUG] Upload failed: {e}")
        return False

def upload_worker(stop_event):
    print("[*] Upload worker started (queue monitor)")
    while not stop_event.is_set():
        # Check if we have files to upload
        if not os.path.exists(CAPTURES_DIR):
            time.sleep(5)
            continue
            
        files = [f for f in os.listdir(CAPTURES_DIR) if f.endswith(".jpg")]
        if not files:
            time.sleep(5)
            continue

        print(f"[DEBUG] Found {len(files)} pening uploads. Checking internet...")
        
        if check_internet():
            print("[DEBUG] Internet connected. Processing queue...")
            for filename in files:
                filepath = os.path.join(CAPTURES_DIR, filename)
                print(f"[Attempting] {filename}")
                
                if send_telegram_photo(filepath):
                    print(f"[SUCCESS] Uploaded {filename}")
                    try:
                        os.remove(filepath)
                    except:
                        pass
                else:
                    print(f"[FAIL] Could not upload {filename}, retrying later.")
        else:
            print("[DEBUG] No internet. Waiting...")
        
        time.sleep(10)  # Check every 10 seconds

# --------------------------------------------------
# CAMERA
# --------------------------------------------------
def capture_intruder():
    """Capture photo instantly with minimal delay"""
    print("[DEBUG] capture_intruder() called")
    
    try:
        cam = cv2.VideoCapture(CAM_INDEX)
        
        # Minimal warmup for instant capture (reduced from 0.6s to 0.2s)
        time.sleep(0.2)
        
        # Try to grab frame immediately
        ret, frame = cam.read()
        
        if ret:
            timestamp = int(time.time())
            filename = f"intruder_{timestamp}.jpg"
            save_path = os.path.join(CAPTURES_DIR, filename)
            cv2.imwrite(save_path, frame)
            print(f"[INFO] ✓ Captured: {save_path}")
        else:
            # Retry once if first attempt fails
            print("[DEBUG] First capture failed, retrying...")
            time.sleep(0.3)
            ret, frame = cam.read()
            if ret:
                timestamp = int(time.time())
                filename = f"intruder_{timestamp}.jpg"
                save_path = os.path.join(CAPTURES_DIR, filename)
                cv2.imwrite(save_path, frame)
                print(f"[INFO] ✓ Captured (retry): {save_path}")
            else:
                print("[ERROR] Failed to grab frame after retry")
        
        cam.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"[ERROR] Capture exception: {e}")

# --------------------------------------------------
# EVENT LOG MONITOR (CORRECT)
# --------------------------------------------------

def monitor_failed_logins(stop_event):
    global last_capture_time

    server = "localhost"
    log_type = "Security"

    handle = win32evtlog.OpenEventLog(server, log_type)

    # 1️⃣ Anchor to latest record using BACKWARDS_READ
    back_flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    events = win32evtlog.ReadEventLog(handle, back_flags, 0)

    if events:
        last_record = events[0].RecordNumber
    else:
        last_record = 0

    print(f"[*] Anchored at record {last_record}")
    print("[*] Monitoring Security log (INSTANT MODE - Fast Detection)")

    # 2️⃣ Switch to forward real-time monitoring
    flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    failed_count = 0

    while not stop_event.is_set():
        try:
            events = win32evtlog.ReadEventLog(handle, flags, 0)

            if not events:
                # Reduced sleep for faster detection (0.1s instead of 1s)
                time.sleep(0.1)
                continue

            for event in events:
                if event.RecordNumber <= last_record:
                    continue

                last_record = event.RecordNumber

                if event.EventID == TARGET_EVENT_ID:
                    failed_count += 1
                    print(f"[ALERT] Failed login #{failed_count} detected (Event 4625)")

                    if failed_count >= FAILED_THRESHOLD:
                        now = time.time()

                        if now - last_capture_time >= CAPTURE_COOLDOWN:
                            print(f"[ACTION] Threshold reached! Capturing NOW...")
                            
                            # Capture in separate thread for non-blocking operation
                            capture_thread = threading.Thread(target=capture_intruder, daemon=True)
                            capture_thread.start()
                            
                            last_capture_time = now
                            print("[INFO] Intruder capture initiated & queued for upload")
                        else:
                            print("[INFO] Capture skipped (cooldown active)")

                        failed_count = 0

            # Faster polling for instant detection (0.1s instead of 0.5s)
            time.sleep(0.1)

        except Exception as e:
            print("[ERROR]", e)
            time.sleep(2)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
def start_monitoring(stop_event):
    thread = threading.Thread(
        target=monitor_failed_logins,
        args=(stop_event,),
        daemon=True
    )
    thread.start()

    upload_thread = threading.Thread(
        target=upload_worker,
        args=(stop_event,),
        daemon=True
    )
    upload_thread.start()

# --------------------------------------------------
# MANUAL TEST MODE
# --------------------------------------------------
if __name__ == "__main__":
    print("[*] Running monitor in test mode...")
    dummy_event = threading.Event()
    start_monitoring(dummy_event)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dummy_event.set()
