# Kobot - Bot Verifikasi & Manajemen Grup Telegram

Kobot adalah bot Telegram multifungsi yang dibuat dengan Python dan library `python-telegram-bot`. Fungsi utamanya adalah sebagai gerbang verifikasi, di mana pengguna harus bergabung ke sebuah channel terlebih dahulu untuk mendapatkan link undangan sekali pakai ke grup utama.

Bot ini juga dilengkapi dengan berbagai fitur administrasi untuk memudahkan pengelolaan komunitas, seperti broadcast pesan, manajemen admin, dan anti-spam.

## 🚀 Fitur Utama

*   **Verifikasi Keanggotaan**: Memaksa pengguna untuk bergabung ke channel sebelum bisa masuk ke grup.
*   **Link Sekali Pakai**: Setiap link undangan yang dibuat hanya berlaku untuk satu pengguna dan akan hangus setelah digunakan.
*   **Panel Kontrol Admin**: Antarmuka berbasis tombol untuk mengakses semua fitur admin dengan mudah.
*   **Broadcast Pesan**: Kirim pesan massal ke semua pengguna yang pernah berinteraksi dengan bot. Mendukung media (foto/video), teks, dan tombol.
*   **Template Broadcast**: Simpan sebuah template broadcast untuk digunakan berulang kali dengan cepat.
*   **Manajemen Admin**: Sistem multi-admin di mana admin utama bisa menambah atau menghapus admin lain.
*   **Pesan Sambutan Kustom**: Atur pesan `/start` sesuai keinginan, lengkap dengan tombol.
*   **Anti-Spam**: Menghapus pesan yang mengandung link dari non-admin di grup utama secara otomatis.

## 🛠️ Daftar Perintah

### Perintah Pengguna
*   `/start` - Memulai bot dan proses verifikasi.
*   `/help` - Menampilkan pesan bantuan.

### Perintah Admin
*   `/admin` - Membuka panel kontrol admin.
*   `/broadcast` - Memulai sesi broadcast interaktif.
*   `/settemplate` - Membuat atau mengubah template broadcast.
*   `/broadcasttemplate` - Mengirim broadcast dari template yang sudah disimpan.
*   `/setwelcome` - Mengatur pesan selamat datang kustom.
*   `/listusers` - Menampilkan daftar semua pengguna bot.
*   `/addadmin <user_id>` - Menambahkan admin baru.
*   `/deladmin <user_id>` - Menghapus admin.
*   `/listadmins` - Menampilkan daftar admin.
*   `/gantichannel <id>` - Mengubah ID channel wajib.
*   `/gantigroup <id>` - Mengubah ID grup utama.
*   `/verifikasiulang <user_id>` - Mengirim ulang link verifikasi ke pengguna.

## ⚙️ Instalasi (Lokal)

1.  **Clone Repositori:**
    ```bash
    git clone https://github.com/linkdewanews/kobot.git
    cd kobot
    ```

2.  **Buat Virtual Environment:**
    Sangat disarankan untuk menggunakan virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependensi:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Bot:**
    Buka file `bot.py` dan edit variabel di bagian `--- Konfigurasi Bot ---`:
    *   `TOKEN`: Token bot Anda dari @BotFather.
    *   `CHANNEL_WAJIB_ID`: ID channel yang harus di-join pengguna.
    *   `GRUP_UTAMA_ID`: ID grup tujuan setelah verifikasi.
    *   `INITIAL_ADMIN_ID`: User ID Telegram Anda untuk dijadikan admin pertama.

5.  **Jalankan Bot:**
    ```bash
    python3 bot.py
    ```

## ☁️ Deploy ke VPS (Systemd)

Metode ini akan membuat bot berjalan sebagai service, yang berarti akan otomatis berjalan saat VPS menyala dan restart jika terjadi crash.

1.  **Upload File Proyek:**
    Upload semua file proyek (`bot.py`, `requirements.txt`, `users.db`, `setup_service.sh`) ke sebuah direktori di VPS, misalnya `/root/kobot`.

2.  **Setup Lingkungan Python:**
    Login ke VPS via SSH, lalu jalankan perintah berikut:
    ```bash
    # Masuk ke direktori proyek
    cd /root/kobot

    # Buat virtual environment
    python3 -m venv venv

    # Aktifkan venv
    source venv/bin/activate

    # Install semua library yang dibutuhkan
    pip install -r requirements.txt

    # Keluar dari venv
    deactivate
    ```

3.  **Jalankan Script Setup Service:**
    Script `setup_service.sh` yang ada di repositori ini akan mengotomatiskan pembuatan file service `systemd`.
    ```bash
    # Beri izin eksekusi pada script
    chmod +x /root/kobot/setup_service.sh

    # Jalankan script
    /root/kobot/setup_service.sh
    ```
    Script ini akan membuat, mengaktifkan, dan menjalankan service secara otomatis.

4.  **Manajemen Service:**
    *   **Melihat status service:**
        ```bash
        sudo systemctl status kobot.service
        ```
    *   **Merestart service (setelah ada perubahan kode):**
        ```bash
        sudo systemctl restart kobot.service
        ```
    *   **Melihat log error:**
        ```bash
        sudo journalctl -u kobot.service -f
        ```

## 📄 Lisensi

Proyek ini dilisensikan di bawah Lisensi MIT.
