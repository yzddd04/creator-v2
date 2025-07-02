# Instagram & TikTok Followers Monitor (Linux & Windows)

Script ini memonitor jumlah followers Instagram dan TikTok secara otomatis menggunakan Playwright dan menyimpan hasilnya ke MongoDB Cloud. Dirancang untuk berjalan di **Linux (termasuk WSL2) dan Windows**.

## Fitur
- Scraping jumlah followers Instagram & TikTok secara real-time
- Penyimpanan data ke MongoDB Cloud
- Otomatisasi browser headless dengan Playwright
- Monitoring multi-user dari database
- Logging penggunaan RAM dan proses Chrome

## Requirement
- Python 3.8+
- MongoDB Cloud (URI sudah diatur di script)
- Koneksi internet
- Linux/WSL2 **atau** Windows

### Python Dependencies
- playwright
- pymongo
- psutil

### System Dependencies (untuk Playwright/Chromium)
#### Linux:
Pastikan library berikut terinstall (umumnya sudah ada di desktop Ubuntu):
```
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libgtk-3-0 libxss1 libasound2 libgbm1 libxshmfence1 libxcomposite1 libxrandr2 libxdamage1 libxfixes3 libxext6 libx11-xcb1 libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libglib2.0-0 fonts-liberation libappindicator3-1 libu2f-udev libvulkan1 libwayland-client0 libwayland-cursor0 libwayland-egl1 libxkbcommon0 libnss3-tools
```
#### Windows:
- Tidak perlu install library tambahan, Playwright akan otomatis mengunduh Chromium dan dependencies yang diperlukan.

## Instalasi (Direkomendasikan: Virtual Environment)
### Linux/WSL2
1. **Install python3-venv jika belum ada:**
   ```bash
   sudo apt-get install python3-venv
   ```
2. **Buat dan aktifkan virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies Python:**
   ```bash
   pip install --upgrade pip
   pip install playwright pymongo psutil
   ```
4. **Install browser Playwright:**
   ```bash
   python3 -m playwright install
   ```

### Windows
1. **Buka Command Prompt (CMD) atau PowerShell**
2. **Buat dan aktifkan virtual environment:**
   ```bat
   py -m venv venv
   .\venv\Scripts\activate
   ```
3. **Install dependencies Python:**
   ```bat
   python -m pip install --upgrade pip
   pip install playwright pymongo psutil
   ```
4. **Install browser Playwright:**
   ```bat
   python -m playwright install
   ```

## Cara Menjalankan
### Linux/WSL2
Aktifkan virtual environment, lalu jalankan script:
```bash
source venv/bin/activate
python3 6_linux.py
```

### Windows
Aktifkan virtual environment, lalu jalankan script:
```bat
.\venv\Scripts\activate
python 6_windows.py
```

## Troubleshooting
- **Error: externally-managed-environment**
  > Gunakan virtual environment (lihat bagian Instalasi di atas).
- **python: command not found**
  > Gunakan `python3` (Linux) atau `python`/`py` (Windows).
- **Browser Playwright gagal launch**
  > Pastikan semua system dependencies sudah terinstall (lihat atas).
- **Koneksi MongoDB gagal**
  > Pastikan URI dan internet benar.

## Catatan
- Script ini sekarang mendukung **Linux/WSL2 dan Windows**.
- Jangan jalankan pip install langsung di sistem, gunakan virtualenv.
- Data MongoDB akan tersimpan di database `creator_web` (ubah URI jika perlu).
- Untuk Windows, gunakan file `6_windows.py`. Untuk Linux, gunakan file `6_linux.py`.

---

**Author:** ahmadyazidarifuddin04 