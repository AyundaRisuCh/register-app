from flask import Flask, request
import pymysql

app = Flask(__name__)

# Konfigurasi database
DB_CONFIG = {
    "host": "py-db.cjqs0i4iie68.ap-southeast-2.rds.amazonaws.com",
    "user": "root",
    "password": "admin123#",
    "database": "sigap_db"
}


# ===========================
# 🔹 REGISTER
# ===========================
@app.route('/register', methods=['POST'])
def register():
    nama = request.form.get('nama')
    email = request.form.get('email')
    no_hp = request.form.get('no_hp')
    password = request.form.get('password')

    if not nama or not email or not no_hp or not password:
        return "Semua field harus diisi", 400

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return "Email sudah terdaftar", 409

        cursor.execute("""
            INSERT INTO users (nama, email, no_hp, password, role)
            VALUES (%s, %s, %s, %s, 'user')
        """, (nama, email, no_hp, password))
        conn.commit()
        return "Pendaftaran berhasil", 200

    except Exception as e:
        return f"Database error: {str(e)}", 500

    finally:
        cursor.close()
        conn.close()


# ===========================
# 🔹 LOGIN
# ===========================
@app.route('/login', methods=['POST'])
def login():
    nama = request.form.get('nama')
    password = request.form.get('password')

    if not nama or not password:
        return "Nama dan password harus diisi", 400

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT role FROM users WHERE nama = %s AND password = %s", (nama, password))
        result = cursor.fetchone()

        if result:
            return result[0]  # hasil: 'admin' atau 'user'
        else:
            return "invalid", 401

    except Exception as e:
        return f"Database error: {str(e)}", 500

    finally:
        cursor.close()
        conn.close()


# ===========================
# 🔹 INSERT DATA BENCANA
# ===========================
@app.route('/insert_bencana', methods=['POST'])
def insert_bencana():
    jenis_bencana = request.form.get('jenis_bencana')
    lokasi = request.form.get('lokasi')

    if not jenis_bencana or not lokasi:
        return "Jenis dan lokasi wajib diisi!", 400

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql = "INSERT INTO data_bencana (jenis_bencana, lokasi) VALUES (%s, %s)"
        cursor.execute(sql, (jenis_bencana, lokasi))
        conn.commit()
        return "Data tersimpan!", 200

    except Exception as e:
        return f"Error: {str(e)}", 500

    finally:
        cursor.close()
        conn.close()


# ===========================
# 🔹 Menampilkan Bencana
# ===========================
from flask import Response
import pymysql

# Route untuk menampilkan data bencana dari Replica
@app.route('/bencana/terbaru', methods=['GET'])
def tampilkan_bencana_terbaru():
    REPLICA_DB_CONFIG = {
        "host": "py-db.cjqs0i4iie68.ap-southeast-2.rds.amazonaws.com",
        "user": "root",
        "password": "admin123#",
        "database": "sigap_db"
    }

    try:
        conn = pymysql.connect(**REPLICA_DB_CONFIG)
        cursor = conn.cursor()

        query = """
            SELECT jenis_bencana, lokasi, DATE_FORMAT(waktu_kejadian, '%%d/%%m/%%Y %%H:%%i') as waktu 
            FROM data_bencana 
            ORDER BY waktu_kejadian DESC 
            LIMIT 50
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return Response("Tidak ada data bencana terbaru.", mimetype='text/plain')

        output = ""
        for row in rows:
            jenis_bencana, lokasi, waktu = row
            output += f"{jenis_bencana} - {lokasi} - {waktu}\n"

        return Response(output, mimetype='text/plain')

    except Exception as e:
        return Response(f"Error: {str(e)}", mimetype='text/plain')

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass



# ===========================
# 🔹 CEK DAN SIMPAN USER + TAMPILKAN SEMUA
#     (Versi dari file PHP)
# ===========================
@app.route('/test_php_convert', methods=['GET', 'POST'])
def test_php_convert():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        response = ""

        if request.method == 'POST':
            nama = request.form.get('nama') or ''
            email = request.form.get('email') or ''
            no_hp = request.form.get('no_hp') or ''

            if nama:
                sql = "INSERT INTO users (nama, email, no_hp) VALUES (%s, %s, %s)"
                cursor.execute(sql, (nama, email, no_hp))
                conn.commit()
                response += "Data tersimpan!<br>"

        # Ambil semua data user
        cursor.execute("SELECT id, nama FROM users")
        rows = cursor.fetchall()

        if rows:
            response += "<h3>Data User:</h3>"
            for row in rows:
                response += f"ID: {row[0]} - Nama: {row[1]}<br>"
        else:
            response += "Tidak ada data."

        return response, 200

    except Exception as e:
        return f"Error: {str(e)}", 500

    finally:
        cursor.close()
        conn.close()


# ===========================
# 🔹 Bedrock Amazon
# ===========================
from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import BotoCoreError, ClientError

app = Flask(__name__)

class Converse:
    def __init__(self):
        self.client = boto3.client(
            'bedrock-runtime',
            region_name='ap-southeast-2'
        )
        self.model_id = 'amazon.nova-micro-v1:0'

    def converse(self, user_message: str):
        conversation = [
            {
                "role": "user",
                "content": [{"text": user_message}]
            }
        ]
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig={
                    "maxTokens": 512,
                    "temperature": 0.5
                }
            )
            return response['output']['message']['content'][0]['text']
        except (BotoCoreError, ClientError) as e:
            return {"error": True, "message": str(e)}
        except Exception as e:
            return {"error": True, "message": str(e)}

@app.route('/converse', methods=['GET', 'POST'])
def handle_converse():
    user_message = request.args.get('message') or request.form.get('message')
    if not user_message:
        return jsonify({"error": True, "message": "Parameter 'message' is required"}), 400

    demo = Converse()
    result = demo.converse(user_message)

    if isinstance(result, str):
        return result
    else:
        return jsonify(result), 500


# ===========================
# 🔹 JALANKAN SERVER
# ===========================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)