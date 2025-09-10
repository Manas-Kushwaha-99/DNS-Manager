# DNS Manager

A modern **Windows-only DNS Manager** built with **Python** and **Flet**, providing a clean graphical interface to manage DNS settings quickly.

This tool makes it simple to switch between popular DNS providers, configure custom servers, reset to automatic, or flush the DNS cache — all without digging through command-line tools.

---

## ✨ Features

* Detect and list all active network adapters
* View current DNS configuration
* One-click switch to popular public DNS providers
* Custom DNS entry support (Primary & Secondary)
* Reset DNS to automatic (DHCP)
* Flush DNS cache easily
* Real-time activity logs with timestamps
* Clean, modern dark UI with icons and presets

---

## 📸 Demo

![DNS MANAGER](https://github.com/user-attachments/assets/9efe3e15-12a2-40b8-b0d6-35b8a1731cb8)

---

## 🛠️ Tech Stack

* **Python 3.10+**
* [Flet](https://flet.dev/) (for GUI)
* Windows PowerShell (for networking commands)
* Multithreading for non-blocking operations

---

## 🚀 Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/DNS-Manager.git
cd DNS-Manager
```

### 2. Install dependencies

```bash
pip install flet
```

### 3. Run the tool

```bash
python dns1.py
```

⚠️ **Note:**

* Requires **Windows** (PowerShell commands won’t work on Linux/macOS).
* Run with **Administrator privileges** for DNS changes to apply.

---

## 📦 Building Executable (Optional)

You can create a `.exe` for easy distribution using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole dns1.py
```

The `.exe` will be available inside the `dist` folder.

---

## 🌐 Supported DNS Presets

* **Google DNS** → Fast and reliable (`8.8.8.8`, `8.8.4.4`)
* **Cloudflare DNS** → Privacy-focused (`1.1.1.1`, `1.0.0.1`)
* **Cloudflare Security** → Malware & phishing protection (`1.1.1.2`, `1.0.0.2`)
* **Quad9** → Privacy + malware protection (`9.9.9.9`, `149.112.112.112`)
* **OpenDNS** → Cisco’s DNS (`208.67.222.222`, `208.67.220.220`)
* **AdGuard DNS** → Ad-blocking DNS (`94.140.14.14`, `94.140.15.15`)
* **Comodo Secure** → Security DNS (`8.26.56.26`, `8.20.247.20`)
* **CleanBrowsing** → Family-friendly filtering (`185.228.168.9`, `185.228.169.9`)
* **DNS.Watch** → German privacy DNS (`84.200.69.80`, `84.200.70.40`)
* **UncensoredDNS** → Unfiltered Danish DNS (`91.239.100.100`, `89.233.43.71`)
* **Mullvad DNS** → Privacy-first DNS from Mullvad VPN (`194.242.2.2`, `194.242.2.3`)
* **Neustar UltraDNS** → Enterprise DNS (`156.154.70.2`, `156.154.71.2`)
* **Yandex DNS** → Russian DNS (`77.88.8.8`, `77.88.8.1`)

---

## 📌 Future Improvements

* Add system tray support
* Cross-platform support (Linux/macOS)
* More DNS providers & custom profiles
* Export/import custom presets

---

## ⚠️ Disclaimer

This project provides a GUI for switching DNS servers using standard Windows PowerShell commands.
All listed DNS providers are **public and legal**, offered by their respective organizations.
The author does not own or operate these DNS services.

---
