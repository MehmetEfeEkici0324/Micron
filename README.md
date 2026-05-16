# 🤖 MICRON — Kişisel Yapay Zeka Asistanı

> Kişiselleştirilmiş yapay zeka asistanı olarak size yardımcı olur 
> Ollama LLM + Ses Tanıma + Akıllı Komut Sistemi

---

## 📁 Proje Yapısı

```
micron/
├── server.py              ← Flask API sunucusu (ana backend)
├── install.py             ← Otomatik kurulum betiği
├── core/
│   └── brain.py           ← AI düşünme motoru
├── voice/
│   └── voice_module.py    ← Ses sistemi
├── ui/
│   └── index.html         ← JARVIS arayüzü (tarayıcıda açılır)
├── skills/
│   └── custom_skills.json ← Özel site/uygulama listesi
└── config/
    └── settings.json      ← Ayarlar (kurulumdan sonra oluşur)
```

---

## 🚀 Kurulum

### 1. Gereksinimler
- Python 3.8+
- Ollama (yerel LLM)
- Mikrofon (ses özelliği için)

### 2. Ollama Kur

**macOS:**
```bash
brew install ollama
# VEYA
curl -fsSL https://ollama.ai/install.sh | sh
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
→ https://ollama.ai/download adresinden indirin

### 3. LLM Model İndir

```bash
# Türkçe için önerilen (iyi Türkçe bilir):
ollama pull llama3

# Alternatifler:
ollama pull llama3.1      # Daha güçlü
ollama pull llama3.2      # Daha hızlı
ollama pull mistral       # Hızlı ve iyi
ollama pull qwen2.5       # Çok dilli, iyi Türkçe
```

### 4. MICRON Kur

```bash
cd micron/
python install.py
```

Bu komut otomatik olarak:
- Python paketlerini yükler (flask, pyttsx3, SpeechRecognition...)
- Ollama'yı kontrol eder
- Başlatma betiği oluşturur

### 5. Başlat

**macOS/Linux:**
```bash
bash start_micron.sh
```

**Windows:**
```
start_micron.bat
```

**Manuel:**
```bash
# Terminal 1:
ollama serve

# Terminal 2:
python server.py

# Tarayıcı:
http://localhost:5000
```

---

## 🎙️ Ses Sistemi Kurulumu

### Web Speech API (Tarayıcı - Önerilen)
Ek kurulum gerekmez! Chrome/Edge kullanın.

Arayüzde "Ses Tanıma" toggle'ını açın.

### Python Ses Modülü
```bash
pip install SpeechRecognition pyttsx3 pyaudio

# Linux'ta ek paket:
sudo apt install portaudio19-dev python3-pyaudio
sudo apt install espeak-ng  # TTS için
```

### Ses Kullanımı
1. Arayüzde ses toggle'ını açın
2. **"Micron, [komut]"** deyin
3. Örnek: *"Micron, Google'ı aç"*
4. Örnek: *"Micron, bugün hava nasıl?"*

---

## 💬 Örnek Komutlar

### Web Siteleri
```
"Google'ı aç"
"YouTube'u aç"
"GitHub'a git"
"Gmail'i açsın"
```

### Uygulamalar
```
"VS Code'u aç"
"Cursor'u başlat"
"Terminal aç"
"Dosya yöneticisini aç"
```

### Proje Açma
```
"VS Code'u aç ve ~/projelerim/web-sitesi klasörüne gir"
"Cursor'u başlat /home/kullanici/projeler/api"
```

### Sistem Komutları
```
"Disk durumunu göster"
"Bellek kullanımı nedir?"
"IP adresim ne?"
```

### Sorular (Ollama LLM)
```
"Python'da async await nasıl çalışır?"
"React hooks nedir?"
"Türkiye'nin nüfusu kaç?"
```

### Arama
```
"Python tutorial ara"
"Hava durumu bugün ara"
```

---

## ⚙️ Özelleştirme

Micron artık ana davranışını `config/settings.json` dosyasından okur. Model, Ollama adresi, wake word, ses dili, TTS hızı, komut zaman aşımı, özel siteler, özel uygulamalar ve proje arama klasörleri buradan yönetilir.

Önemli ayarlar:
```json
{
  "model": "llama3.2:1b",
  "ollama_url": "http://localhost:11434",
  "ollama_autostart": true,
  "wake_word": "micron",
  "language": "tr-TR",
  "response_language": "tr-TR",
  "default_browser": "chrome",
  "speech_command_without_wake_word": true,
  "voice_rate": 0.86,
  "voice_pitch": 0.72,
  "preferred_voice_keywords": ["male", "erkek", "tolga", "microsoft", "tr"],
  "allow_shell_commands": true,
  "project_roots": ["C:/Users/MDH/Desktop", "C:/Users/MDH/Documents"]
}
```

`ollama_autostart` açık olduğunda Micron, Ollama API'ye ulaşamazsa `ollama serve` başlatmayı dener. `model` değeri `ollama list` çıktısındaki model adıyla aynı olmalıdır.

`language` ses tanıma ve TTS dilidir. `response_language` Micron'un cevap dilidir. `default_browser` web komutlarının hangi tarayıcıda açılacağını belirler.

### Yeni Site Ekle
`config/settings.json` içindeki `custom_sites` alanına veya `skills/custom_skills.json` dosyasına ekle:
```json
{
  "web_sites": {
    "sitecim": "https://benim-sitem.com"
  }
}
```

### Yeni Uygulama Ekle
```json
{
  "desktop_apps": {
    "slack": "slack",
    "discord": "discord",
    "zoom": "zoom"
  }
}
```

### Özel Komut Ekle
```json
{
  "custom_commands": {
    "projeyi derle": "cd ~/proje && npm build",
    "sunucuyu yeniden başlat": "sudo systemctl restart nginx"
  }
}
```

### Model Değiştir
Arayüzden açılır menüyü kullanın, ya da `config/settings.json`:
```json
{
  "model": "llama3.2:1b"
}
```

### Ses Algılama
Ses komutları için Chrome/Edge kullanın. Sürekli dinleme açıkken Micron wake word olmadan da komut alabilir; bunu kapatmak isterseniz:
```json
{
  "speech_command_without_wake_word": false
}
```

Micron sesli cevap verirken emoji, markdown işaretleri ve uzun URL'ler temizlenir; bu yüzden TTS emojileri okumaz.

### Öğrenilen Komutlar
Micron'a yeni bir komutu kalıcı olarak öğretebilirsiniz:
```text
"ders modu komutunu sisteme ekle, youtube lo-fi aç"
"haber modu dediğimde google'da son dakika haberleri ara"
```

Sonra sadece şunu yazmanız veya söylemeniz yeterlidir:
```text
"ders modu"
"haber modu"
```

Bu kayıtlar `config/settings.json` içindeki `learned_commands` alanında saklanır.

### Ses Tanıma Network Hatası
Tarayıcıdaki Web Speech API çoğu sistemde internet üzerinden çalışır. `Ses hatası: network` görürseniz bu Micron/Ollama hatası değil, Chrome/Edge'in ses tanıma servisine ulaşamamasıdır. Yazılı komutlar ve öğrenilen komutlar çalışmaya devam eder.

---

## 🔧 Sorun Giderme

### "Ollama bağlantı hatası"
```bash
ollama serve
# Başka terminalde:
ollama list  # Modelleri kontrol et
```

### "Ses tanıma çalışmıyor"
- Chrome veya Edge kullanın (Firefox Web Speech API'yi sınırlı destekler)
- HTTPS veya localhost olması gerekir (zaten localhost çalışıyor)
- Mikrofon izni verin (tarayıcı soracak)

### PyAudio Linux hatası
```bash
sudo apt install portaudio19-dev
pip install pyaudio --break-system-packages
```

### Windows'ta ses problemi
```bash
pip install pyttsx3
# SAPI5 sesi otomatik kullanılır
```

---

## 🛠️ Geliştirme

### API Endpoint'leri
```
POST /api/command    ← Komut gönder
GET  /api/status     ← Sistem durumu
GET  /api/history    ← Konuşma geçmişi
POST /api/clear      ← Geçmişi temizle
POST /api/model      ← Model değiştir
```

### Kendi Skill'ini Yaz
`core/brain.py`'ı açıp `parse_command` fonksiyonuna yeni eşleştirme ekle:

```python
if "proje oluştur" in text_lower:
    return {
        "action": "run_command",
        "target": "mkdir ~/yeni-proje && cd ~/yeni-proje && git init",
        "response": "Proje oluşturuldu!"
    }
```

---

## 📝 Lisans
Mehmet Efe Ekici — Kişisel kullanım için özgürce kullanın.

---

*MICRON* 🤖
