import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
CORS(app)  # Farklı kaynaklardan gelen isteklere izin vermek için (Wix'ten test ederken gerekebilir)

# Veritabanı bağlantı bilgilerini ortam değişkenlerinden al
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')

def get_db_connection():
    """Veritabanına yeni bir bağlantı oluşturur."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode='require' # Neon.tech genellikle SSL gerektirir
        )
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

@app.route('/')
def home():
    return "Kulüp API'sine hoş geldiniz! Liderlik tablosu için /api/leaderboard adresini ziyaret edin."

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Üyelerin puanlarına göre sıralandığı bir liderlik tablosu döndürür (ilk 10 üye).
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Veritabanı bağlantısı kurulamadı."}), 500

        # DictCursor, sonuçları sözlük gibi almanızı sağlar
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Puanı 0'dan büyük olan ilk 10 üyeyi çek
            # Bu sorgu denemeler.py dosyanızdaki update_leaderboard fonksiyonuna benzer
            cur.execute("""
                SELECT name, points
                FROM members
                WHERE points > 0
                ORDER BY points DESC
                LIMIT 10
            """)
            leaderboard_data = cur.fetchall()

        # Veriyi JSON formatına uygun hale getir (DictRow'ları dict'e çevir)
        leaderboard_list = [dict(row) for row in leaderboard_data]

        return jsonify(leaderboard_list)

    except psycopg2.Error as e:
        # Veritabanı ile ilgili bir hata oluşursa
        print(f"Liderlik tablosu alınırken veritabanı hatası: {e}")
        return jsonify({"error": "Veritabanı hatası.", "details": str(e)}), 500
    except Exception as e:
        # Beklenmedik başka bir hata oluşursa
        print(f"Liderlik tablosu alınırken genel hata: {e}")
        return jsonify({"error": "Beklenmedik bir hata oluştu.", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Debug modu geliştirme aşamasında faydalıdır, canlıya alırken kapatılmalıdır.
    # Host='0.0.0.0' API'nin ağdaki diğer cihazlardan erişilebilir olmasını sağlar.
    app.run(debug=True, host='0.0.0.0', port=5000)