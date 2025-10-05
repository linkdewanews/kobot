#!/bin/bash

echo "===== MEMBUAT SYSTEMD SERVICE UNTUK KOBOT ====="

# Menggunakan perintah tee untuk membuat file service dengan sudo
sudo tee /etc/systemd/system/kobot.service > /dev/null <<EOF
[Unit]
Description=Kobot Telegram Service by Gemini
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/kobot
ExecStart=/root/kobot/venv/bin/python3 /root/kobot/bot.py
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

echo "-> File service berhasil dibuat."

# Menjalankan perintah-perintah systemd
echo "-> Menjalankan ulang, mengaktifkan, dan memulai service..."
sudo systemctl daemon-reload
sudo systemctl enable kobot.service
sudo systemctl start kobot.service

echo ""
echo "===== PROSES SELESAI ====="
echo "Cek status service di bawah ini. Pastikan statusnya 'active (running)'."
echo ""

# Menampilkan status akhir
sudo systemctl status kobot.service
