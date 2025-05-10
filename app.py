import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, jsonify, request # 'request' eklendi
from flask_cors import CORS
from dotenv import load_dotenv

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
CORS(app)  # Farklı kaynaklardan gelen isteklere izin vermek için

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
    return "Kulüp API'sine hoş geldiniz! Liderlik tablosu için /api/leaderboard, üye puanları için /api/memberpoints?email=uye@mail.com adresini ziyaret edin."

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Üyelerin puanlarına göre sıralandığı bir liderlik tablosu döndürür (ilk 10 üye).
    Her bir üye objesine Wix Repeater için benzersiz bir '_id' alanı eklenir.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Veritabanı bağlantısı kurulamadı."}), 500

        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT id, name, points
                FROM members
                WHERE points > 0
                ORDER BY points DESC
                LIMIT 10
            """)
            leaderboard_data_from_db = cur.fetchall()

        leaderboard_list_for_wix = []
        if leaderboard_data_from_db:
            for row in leaderboard_data_from_db:
                leaderboard_list_for_wix.append({
                    "_id": str(row["id"]),  # Veritabanındaki 'id'yi string olarak '_id' anahtarına ata
                    "name": row["name"],
                    "points": row["points"]
                })

        return jsonify(leaderboard_list_for_wix)

    except psycopg2.Error as e:
        print(f"Liderlik tablosu alınırken veritabanı hatası: {e}")
        return jsonify({"error": "Veritabanı hatası.", "details": str(e.pgcode) if hasattr(e, 'pgcode') else str(e)}), 500
    except Exception as e:
        print(f"Liderlik tablosu alınırken genel hata: {e}")
        return jsonify({"error": "Beklenmedik bir hata oluştu.", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- YENİ ENDPOINT BAŞLANGICI ---
@app.route('/api/memberpoints', methods=['GET'])
def get_member_points_by_email():
    """
    Verilen e-posta adresine sahip üyenin adını ve puanını döndürür.
    """
    # 1. URL'den 'email' parametresini al
    email_param = request.args.get('email')

    # 2. E-posta parametresi gelmiş mi kontrol et
    if not email_param:
        return jsonify({"error": "E-posta parametresi eksik."}), 400 # Hatalı İstek

    # 3. Veritabanı bağlantısı kur
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Veritabanı bağlantısı kurulamadı."}), 500 # Sunucu Hatası

        # 4. Veritabanı cursor'ı oluştur
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 5. SQL Sorgusu: E-postaya göre üyeyi bul (küçük/büyük harf duyarsız)
            sql_query = """
                SELECT name, points
                FROM members
                WHERE LOWER(email) = LOWER(%s)
            """
            cur.execute(sql_query, (email_param,))
            member_data = cur.fetchone()

        # 6. Üye bulundu mu kontrol et ve yanıtı hazırla
        if member_data:
            return jsonify({
                "name": member_data["name"],
                "points": member_data["points"]
            })
        else:
            # Üye bulunamadı, ancak hata vermek yerine belirli bir mesajla 0 puan döndürelim.
            # Wix tarafı bu "message" alanını kontrol edebilir.
            return jsonify({
                "name": "Kullanıcı Bulunamadı", # Veya "" (boş string)
                "points": 0,
                "message": "Bu e-posta adresi ile kayıtlı üye bulunamadı."
            })

    except psycopg2.Error as db_err:
        error_message = f"Üye puanları alınırken veritabanı hatası (email: {email_param}): {db_err}"
        print(error_message)
        return jsonify({"error": "Veritabanı sorgu hatası.", "details": str(db_err.pgcode) if hasattr(db_err, 'pgcode') else str(db_err)}), 500
    except Exception as e:
        error_message = f"Üye puanları alınırken genel hata (email: {email_param}): {e}"
        print(error_message)
        return jsonify({"error": "Beklenmedik bir sunucu hatası oluştu.", "details": str(e)}), 500
    finally:
        # 7. Veritabanı bağlantısını her zaman kapat
        if conn:
            conn.close()
# --- YENİ ENDPOINT SONU ---

if __name__ == '__main__':
    # Debug modu geliştirme aşamasında faydalıdır, canlıya alırken kapatılmalıdır.
    # Host='0.0.0.0' API'nin ağdaki diğer cihazlardan erişilebilir olmasını sağlar.
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000))) # Render.com için PORT ortam değişkenini kullanabilir
