"""
MICRON - Ses Modülü
Ses tanıma (STT) ve metinden ses sentezi (TTS)
"""

import threading
import queue
import time
import sys
import os
import re


class VoiceModule:
    def __init__(self, wake_word="micron", language="tr-TR", energy_threshold=250, pause_threshold=0.7, phrase_time_limit=12, voice_rate=155, voice_volume=0.95):
        self.wake_word = wake_word.lower()
        self.language = language
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.phrase_time_limit = phrase_time_limit
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        self.is_listening = False
        self.command_queue = queue.Queue()
        self.tts_engine = None
        self._init_tts()
    
    def _init_tts(self):
        """TTS motorunu başlat"""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty("rate", self.voice_rate)
            self.tts_engine.setProperty("volume", self.voice_volume)
            
            # Türkçe ses seç
            voices = self.tts_engine.getProperty("voices")
            best_voice = self._select_jarvis_voice(voices)
            if best_voice:
                self.tts_engine.setProperty("voice", best_voice.id)
            
            print("✅ TTS motoru başlatıldı")
        except ImportError:
            print("⚠️  pyttsx3 yüklü değil: pip install pyttsx3")
        except Exception as e:
            print(f"⚠️  TTS hatası: {e}")
    
    def speak(self, text):
        """Metni sesli söyle"""
        text = self._sanitize_for_speech(text)
        print(f"🔊 MICRON: {text}")
        
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS hata: {e}")
        else:
            # TTS yoksa sistem sesi kullan
            try:
                import platform
                os_type = platform.system().lower()
                if os_type == "darwin":
                    os.system(f'say -v Türkçe "{text}" 2>/dev/null || say "{text}"')
                elif os_type == "linux":
                    os.system(f'espeak-ng -v tr "{text}" 2>/dev/null || espeak "{text}"')
                elif os_type == "windows":
                    os.system(f'powershell -Command "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\\"{text}\\")"')
            except:
                pass
    
    def listen_once(self):
        """Tek seferlik ses dinle"""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.energy_threshold = self.energy_threshold
            r.dynamic_energy_threshold = True
            r.pause_threshold = self.pause_threshold
            r.non_speaking_duration = 0.4
            
            with sr.Microphone() as source:
                print("🎤 Dinleniyor...")
                r.adjust_for_ambient_noise(source, duration=1.0)
                audio = r.listen(source, timeout=7, phrase_time_limit=self.phrase_time_limit)
                
            text = r.recognize_google(audio, language=self.language)
            print(f"🗣️  Duyulan: {text}")
            return text
            
        except ImportError:
            print("⚠️  speech_recognition yüklü değil: pip install SpeechRecognition")
            return None
        except Exception as e:
            print(f"Ses tanıma hatası: {e}")
            return None
    
    def _sanitize_for_speech(self, text):
        """TTS motorunun emoji ve markdown karakterlerini okumasini engeller."""
        text = str(text or "")
        text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text)
        text = re.sub(r"[*_`#>\[\]{}]", "", text)
        text = re.sub(r"https?://\S+", "bağlantı", text)
        return re.sub(r"\s+", " ", text).strip()
    
    def _select_jarvis_voice(self, voices):
        """Mevcut sistem sesleri icinden en tok/Turkce adaya oncelik verir."""
        if not voices:
            return None
        keywords = ["tr", "turkish", "male", "erkek", "tolga", "microsoft"]
        scored = []
        for voice in voices:
            haystack = f"{voice.id} {voice.name}".lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            if "male" in haystack or "erkek" in haystack or "tolga" in haystack:
                score += 3
            if "tr" in haystack or "turkish" in haystack:
                score += 4
            scored.append((score, voice))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]
    
    def start_continuous_listening(self, callback):
        """Sürekli arka planda dinle, wake word algılayınca callback çağır"""
        def listen_loop():
            print(f"👂 '{self.wake_word}' kelimesini bekliyorum...")
            
            while self.is_listening:
                text = self.listen_once()
                
                if text:
                    text_lower = text.lower()
                    
                    # Wake word kontrolü
                    if self.wake_word in text_lower:
                        # Wake word'ü temizle
                        command = text_lower.replace(self.wake_word, "").strip()
                        
                        if command:
                            callback(command)
                        else:
                            # Wake word tek başınaysa, bir sonraki sesi bekle
                            self.speak("Evet, dinliyorum.")
                            command = self.listen_once()
                            if command:
                                callback(command)
                
                time.sleep(0.1)
        
        self.is_listening = True
        thread = threading.Thread(target=listen_loop, daemon=True)
        thread.start()
        print("✅ Ses dinleme başlatıldı")
        return thread
    
    def stop_listening(self):
        """Dinlemeyi durdur"""
        self.is_listening = False
        print("🔇 Ses dinleme durduruldu")


class WebVoiceModule:
    """
    Web tabanlı ses modülü.
    Tarayıcının Web Speech API'sini kullanır.
    Python backend yerine JavaScript ile çalışır.
    """
    
    def get_js_code(self):
        """Tarayıcı ses tanıma için JavaScript kodu"""
        return """
        class MicronVoice {
            constructor(wakeWord = 'micron', onCommand) {
                this.wakeWord = wakeWord.toLowerCase();
                this.onCommand = onCommand;
                this.recognition = null;
                this.synthesis = window.speechSynthesis;
                this.isListening = false;
                this._init();
            }
            
            _init() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    console.warn('Tarayıcınız ses tanımayı desteklemiyor');
                    return;
                }
                
                this.recognition = new SpeechRecognition();
                this.recognition.lang = 'tr-TR';
                this.recognition.continuous = true;
                this.recognition.interimResults = false;
                this.recognition.maxAlternatives = 1;
                
                this.recognition.onresult = (event) => {
                    const text = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
                    console.log('Duyuldu:', text);
                    
                    if (text.includes(this.wakeWord)) {
                        const command = text.replace(this.wakeWord, '').trim();
                        if (command && this.onCommand) {
                            this.onCommand(command);
                        }
                    }
                };
                
                this.recognition.onerror = (event) => {
                    if (event.error !== 'no-speech') {
                        console.log('Ses hatası:', event.error);
                        setTimeout(() => this.start(), 1000);
                    }
                };
                
                this.recognition.onend = () => {
                    if (this.isListening) {
                        setTimeout(() => this.recognition.start(), 100);
                    }
                };
            }
            
            start() {
                if (this.recognition) {
                    this.recognition.start();
                    this.isListening = true;
                    console.log(`'${this.wakeWord}' bekleniyor...`);
                }
            }
            
            stop() {
                if (this.recognition) {
                    this.recognition.stop();
                    this.isListening = false;
                }
            }
            
            speak(text) {
                if (this.synthesis) {
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'tr-TR';
                    utterance.rate = 0.95;
                    utterance.pitch = 1.0;
                    
                    // Türkçe ses seç
                    const voices = this.synthesis.getVoices();
                    const trVoice = voices.find(v => v.lang.includes('tr'));
                    if (trVoice) utterance.voice = trVoice;
                    
                    this.synthesis.speak(utterance);
                }
            }
        }
        """


if __name__ == "__main__":
    voice = VoiceModule()
    voice.speak("Merhaba! Ben Micron, kişisel asistanınız.")
