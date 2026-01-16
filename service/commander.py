import threading
import time
import requests
import json
import os
import ctypes
import sys
from datetime import datetime

# Global configuration
BOT_TOKEN = None
CHAT_ID = None
CAPTURES_DIR = None
stats_manager = None

def init_commander(config, captures_dir):
    global BOT_TOKEN, CHAT_ID, CAPTURES_DIR, stats_manager
    BOT_TOKEN = config['telegram']['bot_token']
    CHAT_ID = str(config['telegram']['chat_id'])
    CAPTURES_DIR = captures_dir
    
    # Initialize statistics manager
    try:
        from service.statistics import StatisticsManager
    except ImportError:
        from statistics import StatisticsManager
    
    db_path = os.path.join(captures_dir, "watchdog_stats.db")
    try:
        stats_manager = StatisticsManager(db_path)
        print(f"[*] Statistics manager initialized in commander")
    except Exception as e:
        print(f"[WARNING] Statistics disabled: {e}")

def send_reply(text):
    """Send text reply to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def send_photo(photo_path, caption=None):
    """Send photo to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": CHAT_ID}
            if caption:
                data["caption"] = caption
            requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")

def execute_command(command_text):
    """Parse and execute commands"""
    cmd = command_text.lower().strip().split()
    if not cmd:
        return

    action = cmd[0]
    print(f"[CMD] Received command: {action}")
    
    # Log command execution
    success = True
    try:
        _execute_command_internal(action, cmd)
    except Exception as e:
        print(f"[ERROR] Command failed: {e}")
        success = False
    
    # Log to statistics
    if stats_manager:
        stats_manager.log_command(action, CHAT_ID, success)

def _execute_command_internal(action, cmd):
    """Internal command execution logic"""

    if action == "/ping":
        send_reply("🏓 Pong! WatchDog is watching. System is online.")

    elif action == "/capture":
        # Lazy import to save RAM
        try:
            from service.camera import capture_intruder_file
        except ImportError:
            from camera import capture_intruder_file
        
        send_reply("📸 Capturing photo...")
        filepath = capture_intruder_file(CAPTURES_DIR, prefix="cmd_")
        if filepath:
            send_photo(filepath, "📸 Remote capture requested")
            try:
                os.remove(filepath)
            except:
                pass
        else:
            send_reply("❌ Camera unavailable")

    elif action == "/screen":
        send_reply("🖥️ Taking screenshot...")
        try:
            import pyautogui
            timestamp = int(time.time())
            filename = f"screen_{timestamp}.png"
            filepath = os.path.join(CAPTURES_DIR, filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            send_photo(filepath, "🖥️ Desktop Screenshot")
            os.remove(filepath)
        except Exception as e:
            send_reply(f"❌ Screenshot failed: {e}")

    elif action == "/lock":
        send_reply("🔒 Locking workstation...")
        try:
            ctypes.windll.user32.LockWorkStation()
            send_reply("✅ System locked.")
        except Exception as e:
            send_reply(f"❌ Lock failed: {e}")

    elif action == "/msg":
        # Usage: /msg Hello Thief
        message = " ".join(cmd[1:])
        if message:
            send_reply(f"📢 Opening Notepad: '{message}'")
            
            def show_notepad_msg(msg):
                import subprocess
                try:
                    # Create a visible text file
                    file_path = os.path.join(CAPTURES_DIR, "MESSAGE_FROM_OWNER.txt")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(msg)
                    
                    # Open Notepad without shell window
                    subprocess.Popen(["notepad.exe", file_path])
                except Exception as e:
                    print(f"[ERROR] Failed to open notepad: {e}")

            threading.Thread(target=show_notepad_msg, args=(message,)).start()
        else:
            send_reply("⚠️ Usage: /msg [Your Message]")
            
    elif action == "/locate":
        send_reply("📡 Scanning WiFi Spectrum & Geolocation...")
        
        def fetch_loc():
            import subprocess
            
            # 1. Scan Nearby WiFi Networks (Triangulation Data)
            wifi_list = []
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output(
                    ["netsh", "wlan", "show", "networks", "mode=bssid"], 
                    startupinfo=si, 
                    encoding="utf-8", 
                    errors="ignore"
                )
                
                current_ssid = "Unknown"
                for line in output.split("\\n"):
                    line = line.strip()
                    if line.startswith("SSID"):
                        # Format: "SSID 1 : Name"
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            current_ssid = parts[1].strip()
                    elif line.startswith("BSSID"):
                        # Format: "BSSID 1 : 00:xx:..."
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            bssid = parts[1].strip()
                            wifi_list.append(f"📶 {current_ssid}\\n   `{bssid}`")
                    elif line.startswith("Signal"):
                         # Add signal to last entry
                         if wifi_list:
                             parts = line.split(":", 1)
                             if len(parts) > 1:
                                 wifi_list[-1] += f" ({parts[1].strip()})"
            except Exception as e:
                wifi_list.append(f"Scan Error: {e}")

            # 2. Get IP & Geo
            try:
                info = requests.get("http://ip-api.com/json/", timeout=10).json()
                if info.get("status") == "success":
                    map_link = f"https://maps.google.com/?q={info['lat']},{info['lon']}"
                    
                    # Format WiFi Data (Top 8 strong signals)
                    wifi_report = "\\n".join(wifi_list[:8]) if wifi_list else "No WiFi networks found."
                    
                    msg = (f"📍 *Detailed Location Report*\\n"
                           f"--------------------------------\\n"
                           f"🌍 *IP-Based Info*:\\n"
                           f"   City: {info['city']}\\n"
                           f"   ISP: {info['isp']}\\n"
                           f"   IP: {info['query']}\\n"
                           f"   🔗 [Google Maps]({map_link})\\n\\n"
                           f"📡 *Nearby WiFi (Triangulation Data)*:\\n"
                           f"{wifi_report}\\n\\n"
                           f"_Copy BSSIDs to Wigle.net for precise coord_")
                    send_reply(msg)
                else:
                    send_reply(f"❌ Geo-IP Failed. WiFi Scan:\\n" + "\\n".join(wifi_list[:5]))
            except Exception as e:
                send_reply(f"❌ Err: {e}")
        
        threading.Thread(target=fetch_loc).start()

    elif action == "/stats":
        send_reply("📊 Generating statistics report...")
        
        def fetch_stats():
            try:
                if not stats_manager:
                    send_reply("❌ Statistics not available")
                    return
                
                stats = stats_manager.get_statistics(days=30)
                message = stats_manager.format_stats_message(stats)
                send_reply(message)
            except Exception as e:
                send_reply(f"❌ Error generating stats: {e}")
        
        threading.Thread(target=fetch_stats).start()
    
    elif action == "/chart":
        send_reply("📈 Generating visual charts...")
        
        def generate_chart():
            try:
                if not stats_manager:
                    send_reply("❌ Statistics not available")
                    return
                
                stats = stats_manager.get_statistics(days=30)
                chart_buffer = stats_manager.generate_chart(stats)
                
                if chart_buffer:
                    # Save chart temporarily
                    chart_path = os.path.join(CAPTURES_DIR, "stats_chart.png")
                    with open(chart_path, "wb") as f:
                        f.write(chart_buffer.read())
                    
                    send_photo(chart_path, "📊 WatchDog Security Statistics")
                    
                    # Clean up
                    try:
                        os.remove(chart_path)
                    except:
                        pass
                else:
                    send_reply("❌ Chart generation failed. Install matplotlib: pip install matplotlib")
            except Exception as e:
                send_reply(f"❌ Error generating chart: {e}")
        
        threading.Thread(target=generate_chart).start()

    elif action == "/help":
        help_text = (
            "🛡️ *WatchDog Command Center*\\n\\n"
            "• /ping - Check status\\n"
            "• /capture - Take photo\\n"
            "• /screen - Screenshot\\n"
            "• /locate - Get Location\\n"
            "• /lock - Lock PC\\n"
            "• /msg [text] - Show popup\\n"
            "• /stats - View statistics\\n"
            "• /chart - Visual graphs"
        )
        send_reply(help_text)

def start_commander_loop():
    """Main polling loop using Long Polling"""
    offset = 0
    print("[*] Commander Service Started (Low-RAM Polling Mode)")
    
    session = requests.Session()
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {
                "offset": offset,
                "timeout": 30  # Wait up to 30s for new message (Low CPU/RAM)
            }
            
            response = session.get(url, params=params, timeout=40)
            result = response.json()

            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update:
                        message = update["message"]
                        user_id = str(message.get("from", {}).get("id"))
                        text = message.get("text", "")
                        
                        # Security: Only accept commands from OWNER
                        if user_id == CHAT_ID and text.startswith("/"):
                            # Run usage intensive tasks in thread
                            threading.Thread(target=execute_command, args=(text,)).start()
                            
        except Exception as e:
            # Silent error handling with backoff
            time.sleep(5)
            
        time.sleep(0.5)
