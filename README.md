# 🔒 WATCHDOG

A lightweight, hidden background service that captures photos of intruders attempting to access your Windows laptop with wrong passwords. Plus, a remote command center controlled via Telegram.

## ✨ Features

- 🚀 **Instant Detection** - Detects failed login attempts in 0.1 seconds
- 📸 **Fast Capture** - Takes photo in 0.5 seconds using webcam
- 📱 **Remote Command Center** - Control your PC via Telegram (`/capture`, `/screen`, `/locate`...)
- 👻 **Hidden Execution** - Runs completely invisible in background
- 🔄 **Auto-Restart** - Survives crashes with 999 retry attempts
- 🌐 **Offline Queue** - Saves photos when offline, uploads when connected
- 🔐 **Boot Protection** - Starts before login on every boot (SYSTEM privileges)
- 📡 **WiFi & Geo Location** - Triangulate location using nearby WiFi networks
- ⚡ **Zero Maintenance** - Set it and forget it

## 📋 Requirements

- Windows 10/11
- Python 3.8+
- Webcam
- Telegram Bot Token & Chat ID

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Telegram

Run the interactive setup script to save your Telegram credentials:

```powershell
python setup/setup_gui.py
```

### 3. Build & Install Service

Run this script to **build the executable** and install the core monitoring service:

**Run as Administrator:**
```powershell
python setup/install_startup.py
```
*This handles the build process (PyInstaller) and sets up the strict Lock Screen Monitor.*

### 4. Enable Full Features (Commander Mode) 🌟

To enable the **Remote Command Center** (ability to send commands like `/screen`, `/locate`, etc.), run the PowerShell script. This creates two specialized tasks:
1. `AntiTheft_Service` (Runs at Boot - WatchDog)
2. `AntiTheft_Commander` (Runs at Login - Telegram Agent)

**Run PowerShell as Administrator:**
```powershell
powershell -ExecutionPolicy Bypass -File "setup/setup.ps1"
```

### 5. Test It

Shut down your laptop, power it back on, and enter 2 wrong PINs at the lock screen. Check your Telegram! Also, only for the first startup it will take ~ 10-12 seconds to run the task on boot, after that it will remain normal as a task.

## 🎮 Remote Commands (Commander)

Once the **Commander** task is running (after logging in), you can send these commands to your bot:

| Command | Description |
| :--- | :--- |
| `/ping` | Check if the system is online and listening. |
| `/capture` | Instantly take a photo using the webcam. |
| `/screen` | Take a silent screenshot of the desktop. |
| `/locate` | Get location report (IP + WiFi Triangulation). |
| `/lock` | Instantly lock the workstation. |
| `/msg "text"` | Pop up a notepad message on the screen (e.g., "Hello Thief"). |
| `/help` | Show list of available commands. |

## 📁 Project Structure

```
Anti-Theft/
├── service/
│   ├── monitor.py          # Main monitoring service
│   ├── commander.py        # Telegram Remote Command Center
│   ├── camera.py           # Camera capture module
│   └── uploader.py         # Telegram upload module
├── setup/
│   ├── setup_gui.py        # Configuration helper
│   ├── install_startup.py  # Builder & Basic Installer
│   └── setup.ps1           # Advanced Dual-Task Installer
├── dist/
│   ├── monitor.exe         # Compiled executable
│   └── config.json         # Configuration file
├── config.json             # Source configuration
├── monitor.spec            # PyInstaller build spec
└── requirements.txt        # Python dependencies
```

## ⚙️ Configuration

Edit `config.json` manually if needed:

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  },
  "security": {
    "failed_attempt_threshold": 2,
    "event_id": 4625,
    "check_interval_seconds": 0.1
  },
  "camera": {
    "device_index": 0
  }
}
```

## 🔧 Management

Run these commands in **PowerShell as Administrator**.

### Check Status
```powershell
schtasks /Query /TN "AntiTheft_Service"
schtasks /Query /TN "AntiTheft_Commander"
```

### Stop All
```powershell
Stop-Process -Name monitor -Force -ErrorAction SilentlyContinue
```

### Uninstall
```powershell
schtasks /Delete /TN "AntiTheft_Service" /F
schtasks /Delete /TN "AntiTheft_Commander" /F
# Or if you only ran install_startup.py:
schtasks /Delete /TN "AntiTheftMonitor" /F
```

## 🛡️ How It Works

1. **System Service (WatchDog)**: Runs as `SYSTEM` on boot. Watches Windows Security Log for `Event 4625`. Triggers webcam capture on wrong password.
2. **User Agent (Commander)**: Runs as `User` on login. Polls Telegram for commands. Executes user-context actions (screenshot, notepad, etc.).

## 🔐 Security Notes

- Runs as SYSTEM user with highest privileges.
- Configuration stored in plain text.
- Photos stored temporarily in `C:\ProgramData\AntiTheftCaptures\` (hidden).

## 🐛 Troubleshooting

### Commander commands not working?
- The Commander only runs **after** a user logs in (it needs a desktop session for screenshots/GUI).
- Ensure `AntiTheft_Commander` task is running: `Get-ScheduledTask | ? TaskName -like "AntiTheft*"`

### Monitor not starting after shutdown?
- Disable Windows Fast Startup in Power Options.
- Check `dist/monitor.exe` exists.

## 📝 License

MIT License - Feel free to use and modify

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

---

**Made by drizzlehx**
