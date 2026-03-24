# 🌐 DNS Manager

A sleek **Windows-only DNS Manager** built with **Python** + **Flet**.
Easily switch between public DNS providers, configure custom servers, reset to automatic, or flush the DNS cache — all with a clean, modern UI.

---

## ✨ Features

* 🔍 Detect and list active network adapters
* 📡 View current DNS configuration
* ⚡ One-click switch to popular public DNS providers
* 🛠️ Add custom DNS (Primary & Secondary)
* 🔄 Reset DNS to automatic (DHCP)
* 🧹 Flush DNS cache instantly
* 📝 Real-time activity log with timestamps
* 🎨 Dark modern interface with icons & presets

---

## 🎥 Demo

![DNS MANAGER](https://github.com/user-attachments/assets/d470b448-3279-4d43-a20c-b70fe8e7c09e)



---

## 🛠️ Tech Stack

* 🐍 Python 3.10+
* 🎨 [Flet](https://flet.dev/) for GUI(Version:0.28.3)
* 💻 Windows PowerShell (network commands)

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Manas-Kushwaha-99/DNS-Manager.git
cd DNS-Manager
```

### 2️⃣ Install dependencies

```bash
pip install flet
```

### 3️⃣ Run the tool

```bash
python DNS-Manager.py
```

⚠️ **Requirements**:

* Works on **Windows only**

---

## 📥 Download

A ready-to-run Windows build is available on GitHub Releases.

**Latest stable release**  
[DNS Manager]([https://github.com/Manas-Kushwaha-99/DNS-Manager/releases/tag/release](https://github.com/Manas-Kushwaha-99/DNS-Manager/releases/tag/2.0))

---

## 🌍 Supported DNS Presets

| Provider             | Primary DNS      | Secondary DNS     | Notes                         |
| -------------------- | ---------------- | ----------------- | ----------------------------- |
| **Google**           | `8.8.8.8`        | `8.8.4.4`         | Fast & reliable               |
| **Cloudflare**       | `1.1.1.1`        | `1.0.0.1`         | Privacy-focused               |
| **Cloudflare Sec**   | `1.1.1.2`        | `1.0.0.2`         | Malware & phishing protection |
| **Quad9**            | `9.9.9.9`        | `149.112.112.112` | Security + privacy            |
| **OpenDNS**          | `208.67.222.222` | `208.67.220.220`  | Cisco’s reliable DNS          |
| **AdGuard**          | `94.140.14.14`   | `94.140.15.15`    | Ad-blocking DNS               |
| **Comodo Secure**    | `8.26.56.26`     | `8.20.247.20`     | Security-focused DNS          |
| **CleanBrowsing**    | `185.228.168.9`  | `185.228.169.9`   | Family-safe filtering         |
| **DNS.Watch**        | `84.200.69.80`   | `84.200.70.40`    | German privacy DNS            |
| **UncensoredDNS**    | `91.239.100.100` | `89.233.43.71`    | Danish, unfiltered            |
| **Mullvad**          | `194.242.2.2`    | `194.242.2.3`     | Privacy-first, Mullvad VPN    |
| **Neustar UltraDNS** | `156.154.70.2`   | `156.154.71.2`    | Enterprise-grade security     |
| **Yandex DNS**       | `77.88.8.8`      | `77.88.8.1`       | Russian DNS w/ multiple modes |

---

## ⚠️ Disclaimer

This project provides a GUI for managing DNS using standard **Windows PowerShell commands**.
All DNS servers listed are **public and legal**, offered by their respective organizations.
The author does **not** own or operate these DNS services.

---

