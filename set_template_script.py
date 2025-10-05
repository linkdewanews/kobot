import sqlite3
import json
import os

# Definisikan path ke database
DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

# Fungsi untuk menyimpan konfigurasi
def set_config(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# Data template yang akan disimpan
template_text = """Serius kamu masih di sini aja? 🤫

Sementara kamu baca pesan ini, member VVIP lagi pada 'main' yang lebih seru lho. Makin lama kamu nunggu, makin banyak momen panas yang kamu lewatin.

Jangan jadi penonton terus dong. Aksi sesungguhnya ada di dalam."""

template_buttons = [
    [
        {"text": "🔥 Intip Keseruan VVIP Sekarang!", "url": "https://idnfy.me/jalurbkp"}
    ]
]
template_buttons_json = json.dumps(template_buttons)

# Proses penyimpanan
try:
    set_config('template_media_type', 'None')
    set_config('template_file_id', 'None')
    set_config('template_text', template_text)
    set_config('template_buttons_json', template_buttons_json)
    print("Template broadcast berhasil disimpan.")
except Exception as e:
    print(f"Gagal menyimpan template: {e}")
