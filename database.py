import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "predictions.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_msg_id INTEGER,
            confirm_msg_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            chat_id INTEGER,
            thread_id INTEGER,
            message_id INTEGER,
            FOREIGN KEY (prediction_id) REFERENCES predictions(id)
        )
    """)
    conn.commit()
    conn.close()

def save_prediction(admin_msg_id: int, confirm_msg_id: int, sent_items: list) -> int:
    """
    Gönderilen tahmin mesajlarını ve yönetici mesaj ID'lerini kaydeder.
    sent_items = [{"chat_id": ..., "thread_id": ..., "message_id": ...}]
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO predictions (admin_msg_id, confirm_msg_id) VALUES (?, ?)",
        (admin_msg_id, confirm_msg_id)
    )
    prediction_id = cursor.lastrowid

    for item in sent_items:
        cursor.execute(
            """
            INSERT INTO sent_messages (prediction_id, chat_id, thread_id, message_id)
            VALUES (?, ?, ?, ?)
            """,
            (prediction_id, item["chat_id"], item.get("thread_id"), item["message_id"])
        )
    conn.commit()
    conn.close()
    return prediction_id

def get_sent_messages_by_reply(reply_msg_id: int) -> list:
    """
    Yöneticinin alıntıladığı mesaj ID'sine ait gruptaki mesajları bulur.
    Admin bota attığı fotoğrafı veya botun onay mesajını alıntılamış olabilir.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sm.chat_id, sm.thread_id, sm.message_id
        FROM sent_messages sm
        JOIN predictions p ON sm.prediction_id = p.id
        WHERE p.confirm_msg_id = ? OR p.admin_msg_id = ?
        """,
        (reply_msg_id, reply_msg_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"chat_id": r[0], "thread_id": r[1], "message_id": r[2]} for r in rows]
