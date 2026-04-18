from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="mdsamim9128",
        database="ai_interview"
    )

@app.route("/questions")
def get_questions():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT question FROM questions WHERE interview_id = 1")
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, port=5001) # Running on different port to avoid conflict
