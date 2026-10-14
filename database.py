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
            match_title TEXT,
            pick TEXT,
            odds TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Eski veritabanı varsa yeni kolonları kontrol et ve ekle
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [col[1] for col in cursor.fetchall()]
    for col_name, col_type in [
        ("match_title", "TEXT"),
        ("pick", "TEXT"),
        ("odds", "TEXT"),
        ("status", "TEXT DEFAULT 'PENDING'")
    ]:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}")

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

def save_prediction(
    admin_msg_id: int,
    confirm_msg_id: int,
    sent_items: list,
    match_title: str = "",
    pick: str = "",
    odds: str = None
) -> int:
    """Yeni tahmini ve gruptaki mesaj ID'lerini kaydeder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO predictions (admin_msg_id, confirm_msg_id, match_title, pick, odds, status)
        VALUES (?, ?, ?, ?, ?, 'PENDING')
        """,
        (admin_msg_id, confirm_msg_id, match_title, pick, odds)
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

def update_prediction_status(reply_msg_id: int, new_status: str):
    """
    Yöneticinin yanıtladığı mesaja ait tahminin durumunu (WON / LOST) günceller.
    İlgili tahmin ID'sini ve gruptaki mesaj listesini döner.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM predictions
        WHERE confirm_msg_id = ? OR admin_msg_id = ?
        ORDER BY id DESC LIMIT 1
        """,
        (reply_msg_id, reply_msg_id)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, []

    prediction_id = row[0]
    cursor.execute(
        "UPDATE predictions SET status = ? WHERE id = ?",
        (new_status, prediction_id)
    )
    conn.commit()

    cursor.execute(
        "SELECT chat_id, thread_id, message_id FROM sent_messages WHERE prediction_id = ?",
        (prediction_id,)
    )
    sent_rows = cursor.fetchall()
    conn.close()
    sent_items = [{"chat_id": r[0], "thread_id": r[1], "message_id": r[2]} for r in sent_rows]
    return prediction_id, sent_items

def get_daily_report_data(hours: int = 24):
    """
    Son 24 saat içinde paylaşılmış tahminlerin istatistiklerini ve listesini döner.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT match_title, pick, odds, status, created_at
        FROM predictions
        WHERE datetime(created_at) >= datetime('now', ?)
        ORDER BY id ASC
        """,
        (f"-{hours} hours",)
    )
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        return None

    won = sum(1 for r in rows if r[3] == "WON")
    lost = sum(1 for r in rows if r[3] == "LOST")
    pending = sum(1 for r in rows if r[3] == "PENDING")

    decided = won + lost
    success_rate = round((won / decided * 100), 1) if decided > 0 else 0

    matches = []
    for r in rows:
        title = r[0] or "Karşılaşma"
        pick = r[1] or "Tercih"
        st = r[3]
        if st == "WON":
            icon = "✅"
        elif st == "LOST":
            icon = "✖️"
        else:
            icon = "⏳"
        matches.append({
            "title": title,
            "pick": pick,
            "odds": r[2],
            "status": st,
            "icon": icon
        })

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "success_rate": success_rate,
        "matches": matches
    }
