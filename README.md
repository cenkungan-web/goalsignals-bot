# Telegram Topic Dağıtıcı Bot

Bu bot, yöneticinin özel mesajdan gönderdiği kupon/tahmin fotoğraflarını ve tercihlerini otomatik olarak algılar, şablonlar ve belirlenen Telegram gruplarındaki özel topic'lere (konulara) dağıtır.

## Özellikler
- **Otomatik Şablonlama:**
  - Sadece tercih yazarsanız (örn: `MS 10.5 ÜST Korner`) ➡️ **Oransız Şablon**.
  - Yanına oran eklerseniz (örn: `MS 1.5 ÜST O 1.70` veya `KG VAR O: 1.85`) ➡️ **Oranlı Şablon**.
- **Doğrudan Topic Desteği:** Belirtilen `chat_id` ve `message_thread_id` değerlerine doğrudan gönderir.
- **Güvenlik:** Sadece tanımlanan `ADMIN_IDS` sahiplerinin mesajlarını iletir.
- **Koyeb & Render Uyumlu:** Dahili HTTP portu sayesinde 7/24 ücretsiz servislerde uykuya dalmadan veya sağlık kontrolü hatası vermeden çalışır.

---

## 1. Kendi Bilgisayarınızda Test Etme

1. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
2. `.env.example` dosyasının bir kopyasını oluşturup adını `.env` yapın ve bilgilerinizi girin:
   ```env
   BOT_TOKEN=BotFather_Tokeniniz
   ADMIN_IDS=Kendi_Telegram_IDniz
   TARGET_TOPICS=-1001234567890:42,-1009876543210:105
   ```
3. Botu başlatın:
   ```bash
   python main.py
   ```

---

## 2. Topic ve Grup ID'lerini Nasıl Bulurum?

1. Botu hedef gruba ekleyin ve yönetici yetkisi verin.
2. Hedef gruptaki göndermek istediğiniz Topic'in içine girip `/id` yazın.
3. Bot size grubun Chat ID'sini ve o konunun Topic ID'sini verecektir.

---

## 3. Koyeb'e 7/24 Ücretsiz Yükleme (Adım Adım)

1. Bir **GitHub** hesabı açın (yoksa) ve bu klasörü yeni bir repository (depo) olarak yükleyin.
2. [Koyeb.com](https://www.koyeb.com)'a ücretsiz üye olun.
3. **Create Service** > **GitHub** seçeneğine tıklayın ve deponuzu seçin.
4. **Environment Variables** (Ortam Değişkenleri) kısmına şunları ekleyin:
   - `BOT_TOKEN`: Telegram bot tokenınız
   - `ADMIN_IDS`: Telegram ID'niz
   - `TARGET_TOPICS`: Hedefleriniz (örn: `-1001234567890:42`)
5. **Deploy** butonuna tıklayın.
   - Botunuz birkaç saniye içinde derlenip 7/24 kesintisiz çalışmaya başlayacaktır!
