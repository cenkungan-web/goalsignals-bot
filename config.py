import os
import re
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8644398637:AAEd6WfM2BEyqXIO2J1Uhwvx6lZjZXoPO7Q")

# Google Gemini API Anahtarı (Görsel okuma için)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# İzinli Kullanıcı Adları (Sadece bu kullanıcılar bota yazabilir)
ALLOWED_USERNAMES = ["uki1905"]

# İzinli Telegram ID'leri (Opsiyonel ID ile kontrol)
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_RAW.split(",") if i.strip().isdigit()]

# Hedef Topic Listesi
# 1. Goal Signals Sohbet -> Topic ID: 137759 (Chat ID: -1002306074930)
# 2. Özel Grup -> Topic ID: 3 (Chat ID: -1002045978218)
TARGET_DESTINATIONS = [
    {
        "name": "Goal Signals Sohbet",
        "chat_id": -1002306074930,
        "thread_id": 137759
    },
    {
        "name": "Özel Grup",
        "chat_id": -1002045978218,
        "thread_id": 3
    }
]

def get_target_destinations():
    # Eğer ortam değişkeninde özel liste varsa onu kullan, yoksa sabit tanımlıları dön
    targets_env = os.getenv("TARGET_TOPICS", "")
    if targets_env:
        custom_destinations = []
        for item in targets_env.split(","):
            parts = item.strip().split(":")
            if len(parts) == 2:
                try:
                    custom_destinations.append({
                        "name": f"Grup {parts[0]}",
                        "chat_id": int(parts[0]),
                        "thread_id": int(parts[1])
                    })
                except ValueError:
                    pass
        if custom_destinations:
            return custom_destinations
    return TARGET_DESTINATIONS

PORT = int(os.getenv("PORT", 8080))

# ----------------- ŞABLONLAR -----------------

# 1. TAHMİN ŞABLONLARI
TEMPLATE_WITHOUT_ODDS = (
    "⚽️ <b>{home_team} - {away_team} ({score})</b>\n"
    "🏟 <b>{league}</b>\n"
    "⏰ <b>{minute}</b>\n"
    "🎯 <b>{tercih}</b>\n\n"
    '🔗 <a href="https://goalsignals.com.tr">GoalSignals.Com.Tr</a>'
)

TEMPLATE_WITH_ODDS = (
    "⚽️ <b>{home_team} - {away_team} ({score})</b>\n"
    "🏟 <b>{league}</b>\n"
    "⏰ <b>{minute}</b>\n"
    "🎯 <b>{tercih}</b>\n"
    "💰 <b>Oran:</b> {oran}\n\n"
    '🔗 <a href="https://goalsignals.com.tr">GoalSignals.Com.Tr</a>'
)

# 2. SONUÇLANDIRMA (W / L) ŞABLONLARI
WIN_TEMPLATE = (
    "✅ <b>Kazandı</b>\n"
    "🎁 <b>Değerlendiren arkadaşları tebrik ederiz</b>\n"
    '🔗 <a href="https://goalsignals.com.tr">GoalSignals.Com.Tr</a>'
)

LOSS_TEMPLATE = (
    "✖️ <b>Kaybetti</b>\n"
    '🔗 <a href="https://goalsignals.com.tr">GoalSignals.Com.Tr</a>'
)

def parse_caption(raw_text: str) -> dict:
    if not raw_text:
        return {"tercih": "Canlı Tercih", "oran": None}

    raw_text = raw_text.strip()
    match = re.search(r'\s+[Oo](?:ran)?[:\s]+([0-9]+[.,]?[0-9]*)', raw_text)
    
    if match:
        oran = match.group(1).replace(',', '.')
        tercih = raw_text[:match.start()].strip()
        return {"tercih": tercih, "oran": oran}
    
    return {"tercih": raw_text, "oran": None}

def build_prediction_caption(match_info: dict, parsed_caption: dict) -> str:
    data = {
        "home_team": match_info.get("home_team", "Ev Sahibi"),
        "away_team": match_info.get("away_team", "Deplasman"),
        "score": match_info.get("score", "0-0"),
        "league": match_info.get("league", "Lig"),
        "minute": match_info.get("minute", "Canlı"),
        "tercih": parsed_caption.get("tercih", ""),
        "oran": parsed_caption.get("oran")
    }

    if data["oran"]:
        return TEMPLATE_WITH_ODDS.format(**data)
    else:
        return TEMPLATE_WITHOUT_ODDS.format(**data)

def build_daily_report(report_data: dict, date_str: str) -> str:
    """Gün sonu rapor metnini formatlar."""
    total = report_data["total"]
    won = report_data["won"]
    lost = report_data["lost"]
    pending = report_data["pending"]
    rate = report_data["success_rate"]

    match_lines = []
    for m in report_data["matches"]:
        odds_str = f" @ {m['odds']}" if m.get("odds") else ""
        match_lines.append(f"{m['icon']} {m['title']} ({m['pick']}{odds_str})")

    matches_text = "\n".join(match_lines)

    report = (
        "📊 <b>GOALSIGNALS GÜN SONU RAPORU</b> 📊\n"
        f"📅 <b>Tarih:</b> {date_str}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Toplam Tahmin:</b> {total}\n"
        f"✅ <b>Kazanan:</b> {won}\n"
        f"✖️ <b>Kaybeden:</b> {lost}\n"
    )

    if pending > 0:
        report += f"⏳ <b>Sonuçlanmamış / Devam Eden:</b> {pending}\n"

    report += (
        f"📈 <b>Başarı Oranı:</b> %{rate}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Günün Karşılaşmaları:</b>\n"
        f"{matches_text}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 <i>Tüm kazanan üyelerimizi tebrik eder, yarın için bol şanslar dileriz!</i>\n\n"
        '🔗 <a href="https://goalsignals.com.tr">GoalSignals.Com.Tr</a>'
    )
    return report

