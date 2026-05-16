#!/usr/bin/env python3
"""
MICRON Kurulum Betiği
Tüm bağımlılıkları yükler ve sistemi hazırlar
"""

import subprocess
import sys
import os
import platform
import json
import urllib.request
import shutil


def run(cmd, check=True):
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ✗ Hata: {result.stderr[:200]}")
        return False
    if result.stdout:
        print(f"    {result.stdout.strip()[:100]}")
    return True


def check_python():
    ver = sys.version_info
    if ver.major < 3 or ver.minor < 8:
        print(f"✗ Python 3.8+ gerekli. Mevcut: {ver.major}.{ver.minor}")
        sys.exit(1)
    print(f"✅ Python {ver.major}.{ver.minor}.{ver.micro}")


def install_packages():
    packages = [
        "flask",
        "flask-cors",
        "requests",
        "pyttsx3",
        "SpeechRecognition",
        "pyaudio",
    ]
    
    print("\n📦 Python paketleri yükleniyor...")
    for pkg in packages:
        print(f"  Installing {pkg}...")
        run(f"{sys.executable} -m pip install {pkg} -q", check=False)
    
    print("✅ Paketler yüklendi")


def check_ollama():
    print("\n🦙 Ollama kontrol ediliyor...")
    
    result = subprocess.run("ollama --version", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Ollama mevcut: {result.stdout.strip()}")
        return True
    
    print("⚠️  Ollama bulunamadı. Yükleme talimatları:")
    os_type = platform.system().lower()
    
    if os_type == "darwin":
        print("   → brew install ollama")
        print("   → veya: https://ollama.ai/download")
    elif os_type == "linux":
        print("   → curl -fsSL https://ollama.ai/install.sh | sh")
    elif os_type == "windows":
        print("   → https://ollama.ai/download adresinden indirin")
    
    return False


def pull_model(model="llama3"):
    print(f"\n🧠 {model} modeli indiriliyor... (Bu birkaç dakika sürebilir)")
    
    # Ollama servis çalışıyor mu?
    result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("  Ollama servisi başlatılıyor...")
        subprocess.Popen("ollama serve", shell=True)
        import time; time.sleep(3)
    
    if run(f"ollama pull {model}", check=False):
        print(f"✅ {model} hazır")
    else:
        print(f"⚠️  {model} indirilemedi. 'ollama pull {model}' komutunu elle çalıştırın")


def create_config():
    config = {
        "model": "llama3",
        "wake_word": "micron",
        "language": "tr-TR",
        "voice_enabled": True,
        "server_port": 5000,
        "auto_start_browser": True,
        "custom_apps": {},
        "custom_sites": {}
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Ayarlar: {config_path}")


def create_launch_scripts():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os_type = platform.system().lower()
    
    if os_type in ("darwin", "linux"):
        script = f"""#!/bin/bash
echo "🤖 MICRON başlatılıyor..."
cd "{base_dir}"

# Ollama kontrol
if ! pgrep -x "ollama" > /dev/null; then
    echo "🦙 Ollama başlatılıyor..."
    ollama serve &
    sleep 2
fi

# MICRON sunucusu
echo "📡 Sunucu başlatılıyor..."
{sys.executable} server.py &
sleep 2

# Tarayıcı aç
echo "🌐 Arayüz açılıyor..."
{('open' if os_type == 'darwin' else 'xdg-open')} http://localhost:5000

echo "✅ MICRON hazır! Ctrl+C ile durdurun."
wait
"""
        script_path = os.path.join(base_dir, "start_micron.sh")
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        print(f"✅ Başlatma betiği: {script_path}")
        print(f"   Çalıştır: bash {script_path}")
    
    elif os_type == "windows":
        script = f"""@echo off
echo MICRON baslatiliyor...
cd /d "{base_dir}"
start "Ollama" /min ollama serve
timeout /t 2 /nobreak > nul
start "MICRON Server" {sys.executable} server.py
timeout /t 2 /nobreak > nul
start http://localhost:5000
echo MICRON hazir!
pause
"""
        script_path = os.path.join(base_dir, "start_micron.bat")
        with open(script_path, "w") as f:
            f.write(script)
        print(f"✅ Başlatma betiği: {script_path}")
        print(f"   Çalıştır: {script_path}")


def main():
    print("=" * 50)
    print("   🤖 MICRON Kurulum Betiği")
    print("=" * 50)
    
    check_python()
    install_packages()
    
    has_ollama = check_ollama()
    if has_ollama:
        pull_model("llama3")
    
    create_config()
    create_launch_scripts()
    
    print("\n" + "=" * 50)
    print("✅ Kurulum tamamlandı!")
    print("\n🚀 Başlatmak için:")
    
    os_type = platform.system().lower()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os_type == "windows":
        print(f"   start_micron.bat")
    else:
        print(f"   bash {os.path.join(base_dir, 'start_micron.sh')}")
    
    print("\n📖 Veya manuel:")
    print(f"   ollama serve  (ayrı terminalde)")
    print(f"   python {os.path.join(base_dir, 'server.py')}")
    print(f"   Tarayıcı: http://localhost:5000")
    print("=" * 50)


if __name__ == "__main__":
    main()
