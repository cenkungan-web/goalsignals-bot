import json
import logging
import re
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODELS_TO_TRY = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite"
]

def format_minute_text(minute_val: str) -> str:
    """Dakika metnini düzenler (Örn: '82:27' ise '83. Dakika')."""
    if not minute_val:
        return "Canlı"
    minute_val = str(minute_val).strip()
    match = re.match(r"^(\d+):(\d+)$", minute_val)
    if match:
        mins = int(match.group(1)) + 1
        return f"{mins}. Dakika"
    if "dakika" not in minute_val.lower() and minute_val.isdigit():
        return f"{minute_val}. Dakika"
    return minute_val

def extract_match_info(image_bytes: bytes, api_key: str) -> dict:
    default_info = {
        "home_team": "Ev Sahibi",
        "away_team": "Deplasman",
        "score": "0-0",
        "league": "Lig",
        "minute": "Canlı"
    }

    if not api_key:
        logger.warning("GEMINI_API_KEY bulunamadı!")
        return default_info

    client = genai.Client(api_key=api_key)
    prompt = (
        "Analyze this sports match screenshot and extract current match details.\n"
        "Extract:\n"
        "- home_team: Full name of home team\n"
        "- away_team: Full name of away team\n"
        "- score: Current score (e.g. 7-3 or 0-2)\n"
        "- league: League, Cup or tournament name\n"
        "- minute: Current match minute (e.g. 83. Dakika or 82:27)\n\n"
        "Return ONLY a valid JSON object with keys: home_team, away_team, score, league, minute.\n"
        "Do not include any extra text, commentary, or markdown formatting."
    )

    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt
                ]
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text).strip()

            data = json.loads(raw_text)
            raw_minute = data.get("minute") or "Canlı"
            formatted_minute = format_minute_text(raw_minute)

            # Skor formatını düzenle (7 : 3 -> 7-3)
            raw_score = str(data.get("score") or "0-0").replace(":", "-").replace(" ", "")

            return {
                "home_team": data.get("home_team") or default_info["home_team"],
                "away_team": data.get("away_team") or default_info["away_team"],
                "score": raw_score,
                "league": data.get("league") or default_info["league"],
                "minute": formatted_minute,
            }
        except Exception as e:
            logger.warning(f"Model {model_name} ile okunamadı, diğer modele geçiliyor: {e}")

    logger.error("Tüm Gemini modelleri başarısız oldu.")
    return default_info
