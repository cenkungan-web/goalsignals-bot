import asyncio
import io
import logging
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

from telegram import LinkPreviewOptions, Update, User
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database
import ocr

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Koyeb / Render için arka plan HTTP sunucusu
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"GoalSignals Telegram Bot Aktif!")

    def log_message(self, format, *args):
        return

def start_health_server():
    server = HTTPServer(("0.0.0.0", config.PORT), HealthHandler)
    logger.info(f"Healthcheck HTTP sunucusu {config.PORT} portunda devrede.")
    server.serve_forever()

def is_authorized(user: User) -> bool:
    """Yalnızca yetkili kullanıcılara izin verir (Örn: uki1905)."""
    if not user:
        return False
    username = (user.username or "").lower().strip()
    allowed_list = [u.lower().strip() for u in config.ALLOWED_USERNAMES]
    if username in allowed_list:
        return True
    if user.id in config.ADMIN_IDS:
        return True
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user):
        return

    text = (
        f"🤖 <b>GoalSignals Canlı Tahmin Botu</b>\n\n"
        f"Hoş geldin @{user.username}!\n"
        f"Kullanıcı ID'niz: <code>{user.id}</code>\n\n"
        f"<b>Nasıl Kullanılır?</b>\n"
        f"1. Maç görselini seçin.\n"
        f"2. Açıklama kısmına tercihinizi yazın:\n"
        f"   • <i>Oransız:</i> <code>10.5 ÜST KORNER</code>\n"
        f"   • <i>Oranlı:</i> <code>10.5 ÜST KORNER O 1.85</code>\n"
        f"3. Bot görseldeki takımları, skoru, dakikayı ve ligi okuyup 2 hedefe de iletir.\n\n"
        f"<b>Sonuçlandırma:</b>\n"
        f"Tahmin paylaşıldığında botun size atacağı mesaja yanıt (reply) verip:\n"
        f"• <code>W</code> ➡️ Kazandı alıntısı\n"
        f"• <code>L</code> ➡️ Kaybetti alıntısı\n\n"
        f"<b>Komutlar:</b>\n"
        f"• <code>/rapor</code> : Günün durumunu önizler.\n"
        f"• <code>/rapor yayinla</code> : Gün sonu raporunu kanallara hemen iletir.\n"
        f"• <code>/targets</code> : Tanımlı hedef kanalları listeler.\n"
        f"• <code>/id</code> : Bulunduğunuz yerin ID bilgilerini gösterir."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user):
        return

    chat = update.effective_chat
    thread_id = update.message.message_thread_id

    response = (
        f"📋 <b>Bilgiler:</b>\n"
        f"• <b>Sohbet ID:</b> <code>{chat.id}</code>\n"
        f"• <b>Sohbet Adı:</b> {chat.title or 'Özel Mesaj'}\n"
        f"• <b>Topic ID:</b> <code>{thread_id or 'Genel Konu / Yok'}</code>\n"
        f"• <b>Sizin User ID:</b> <code>{user.id}</code>\n"
        f"• <b>Kullanıcı Adı:</b> @{user.username}"
    )
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

async def targets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user):
        return

    destinations = config.get_target_destinations()
    msg = "🎯 <b>Tanımlı Hedef Topic'ler:</b>\n\n"
    for idx, d in enumerate(destinations, 1):
        name = d.get("name", "Hedef")
        msg += f"{idx}. <b>{name}</b>\n   • Chat ID: <code>{d['chat_id']}</code>\n   • Topic ID: <code>{d['thread_id']}</code>\n\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def rapor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminin gün sonu raporunu elle görüntülemesini veya yayınlamasını sağlar."""
    user = update.effective_user
    if not is_authorized(user):
        return

    tz = ZoneInfo("Europe/Istanbul")
    now = datetime.now(tz)
    date_display = now.strftime("%d.%m.%Y")

    report_data = database.get_daily_report_data(hours=24)
    if not report_data or report_data["total"] == 0:
        await update.message.reply_text(
            f"ℹ️ Son 24 saat içinde kaydedilmiş herhangi bir tahmin bulunmuyor ({date_display})."
        )
        return

    report_text = config.build_daily_report(report_data, date_display)

    # Argüman kontrolü (/rapor yayinla)
    args = context.args or []
    if len(args) > 0 and args[0].lower() in ["yayinla", "gonder", "send"]:
        destinations = config.get_target_destinations()
        sent_count = 0
        for target in destinations:
            try:
                await context.bot.send_message(
                    chat_id=target["chat_id"],
                    message_thread_id=target.get("thread_id"),
                    text=report_text,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Rapor gönderilemedi: {target['chat_id']} -> {e}")

        await update.message.reply_text(
            f"✅ Gün sonu raporu başarıyla {sent_count} topic'e yayınlandı!\n\n{report_text}",
            parse_mode=ParseMode.HTML
        )
    else:
        # Sadece önizleme göster
        await update.message.reply_text(
            f"👀 <b>GÜN SONU RAPOR ÖNİZLEMESİ:</b>\n\n{report_text}\n\n"
            f"👉 <i>Bu raporu kanallara yayınlamak için:</i> <code>/rapor yayinla</code> yazabilirsiniz.",
            parse_mode=ParseMode.HTML
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user):
        return

    destinations = config.get_target_destinations()
    status_msg = await update.message.reply_text("⏳ Görsel analiz ediliyor ve maç bilgileri okunuyor...")

    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()

        # Gemini Vision ile maç bilgilerini oku
        match_info = ocr.extract_match_info(bytes(photo_bytes), config.GEMINI_API_KEY)

        # Tercih ve oranı ayrıştır
        raw_caption = update.message.caption or ""
        parsed_caption = config.parse_caption(raw_caption)

        # Şablonlu metni oluştur
        final_caption = config.build_prediction_caption(match_info, parsed_caption)

        sent_items = []
        errors = []

        for target in destinations:
            try:
                sent_msg = await context.bot.send_photo(
                    chat_id=target["chat_id"],
                    message_thread_id=target.get("thread_id"),
                    photo=photo.file_id,
                    caption=final_caption,
                    parse_mode=ParseMode.HTML
                )
                sent_items.append({
                    "chat_id": target["chat_id"],
                    "thread_id": target.get("thread_id"),
                    "message_id": sent_msg.message_id
                })
            except Exception as e:
                err_text = f"Chat: {target['chat_id']} ({target.get('thread_id')}) -> {e}"
                logger.error(err_text)
                errors.append(err_text)

        await status_msg.delete()

        match_title = f"{match_info['home_team']} - {match_info['away_team']}"

        confirm_text = (
            f"✅ <b>Tahmin Paylaşıldı!</b> ({len(sent_items)}/{len(destinations)} Topic)\n\n"
            f"<b>Okunan Maç:</b>\n"
            f"⚽️ {match_title} ({match_info['score']})\n"
            f"🏟 {match_info['league']}\n"
            f"⏰ {match_info['minute']}\n"
            f"🎯 Tercih: {parsed_caption['tercih']}\n"
        )
        if parsed_caption.get("oran"):
            confirm_text += f"💰 Oran: {parsed_caption['oran']}\n"

        confirm_text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 <b>Sonuçlandırmak için BU MESAJI yanıtlayarak (reply):</b>\n"
            f"• <code>W</code> ➡️ Kazandı alıntısı\n"
            f"• <code>L</code> ➡️ Kaybetti alıntısı"
        )

        if errors:
            confirm_text += "\n\n⚠️ <b>Bazı Hatalar:</b>\n" + "\n".join(errors[:3])

        confirm_msg = await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)

        # Veritabanına detaylı kaydet (Rapor ve alıntılama için)
        database.save_prediction(
            admin_msg_id=update.message.message_id,
            confirm_msg_id=confirm_msg.message_id,
            sent_items=sent_items,
            match_title=match_title,
            pick=parsed_caption["tercih"],
            odds=parsed_caption.get("oran")
        )

    except Exception as e:
        logger.error(f"Hata: {e}")
        await status_msg.edit_text(f"❌ Bir hata oluştu: {e}")

async def handle_result_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """uki1905 'W' veya 'L' ile bir mesaja reply yaptığında devreye girer."""
    user = update.effective_user
    if not is_authorized(user):
        return

    text = (update.message.text or "").strip().upper()
    if text not in ["W", "L"]:
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    new_status = "WON" if text == "W" else "LOST"
    prediction_id, sent_items = database.update_prediction_status(reply.message_id, new_status)
    if not sent_items:
        await update.message.reply_text("⚠️ Alıntıladığınız mesaja ait kayıtlı bir tahmin bulunamadı.")
        return

    if text == "W":
        result_text = config.WIN_TEMPLATE
        status_label = "✅ Kazandı"
    else:
        result_text = config.LOSS_TEMPLATE
        status_label = "✖️ Kaybetti"

    success_count = 0
    for item in sent_items:
        try:
            await context.bot.send_message(
                chat_id=item["chat_id"],
                message_thread_id=item.get("thread_id"),
                text=result_text,
                reply_to_message_id=item["message_id"],
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Sonuç gönderilemedi ({item['chat_id']}): {e}")

    await update.message.reply_text(
        f"🎯 <b>Sonuç İletildi:</b> {status_label}\n"
        f"📢 {success_count} topic'teki kupon doğrudan alıntılanarak sonuçlandırıldı!",
        parse_mode=ParseMode.HTML
    )

# ----------------- GECE 01:00 GÜN SONU RAPORU ZAMANLAYICISI -----------------

async def daily_report_scheduler(app: Application):
    """
    Her gece Türkiye saatiyle 01:00'da kontrol eder.
    Eğer son 24 saatte tahmin paylaşılmışsa gün sonu raporunu otomatik kanallara gönderir.
    Eğer hiç tahmin atılmamışsa hiçbir şey yapmaz.
    """
    tz = ZoneInfo("Europe/Istanbul")
    last_reported_date = None

    logger.info("Gün sonu rapor zamanlayıcısı devrede (Hedef: Her gece 01:00).")

    while True:
        try:
            now = datetime.now(tz)
            current_date_str = now.strftime("%Y-%m-%d")

            # Gece 01:00 kontrolü
            if now.hour == 1 and now.minute == 0 and last_reported_date != current_date_str:
                yesterday = now - timedelta(days=1)
                date_display = yesterday.strftime("%d.%m.%Y")

                report_data = database.get_daily_report_data(hours=24)
                if report_data and report_data["total"] > 0:
                    report_text = config.build_daily_report(report_data, date_display)
                    destinations = config.get_target_destinations()
                    for target in destinations:
                        try:
                            await app.bot.send_message(
                                chat_id=target["chat_id"],
                                message_thread_id=target.get("thread_id"),
                                text=report_text,
                                parse_mode=ParseMode.HTML,
                                link_preview_options=LinkPreviewOptions(is_disabled=True)
                            )
                        except Exception as e:
                            logger.error(f"Otomatik rapor gönderilemedi: {target['chat_id']} -> {e}")

                    logger.info(f"{date_display} tarihli gün sonu raporu kanallara iletildi.")
                    last_reported_date = current_date_str

        except Exception as e:
            logger.error(f"Scheduler hatası: {e}")

        # Her 30 saniyede bir saati kontrol et
        await asyncio.sleep(30)

async def post_init(application: Application):
    """Bot ayağa kalktıktan sonra zamanlayıcıyı başlatır."""
    asyncio.create_task(daily_report_scheduler(application))

def main():
    if not config.BOT_TOKEN:
        print("HATA: BOT_TOKEN girilmemiş!")
        return

    database.init_db()
    threading.Thread(target=start_health_server, daemon=True).start()

    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("targets", targets_command))
    app.add_handler(CommandHandler("rapor", rapor_command))

    # Özel mesajdan gelen fotoğraflar
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo))

    # W / L sonuç yanıtları
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.REPLY, handle_result_reply))

    logger.info("GoalSignals Bot Başlatıldı...")
    app.run_polling()

if __name__ == "__main__":
    main()
