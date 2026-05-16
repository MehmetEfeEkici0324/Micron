"""
MICRON - API Sunucusu
Web arayüzü ile Python backend arasındaki köprü
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import threading
import subprocess
import webbrowser
import platform
import time
import re
import requests
from datetime import datetime

app = Flask(__name__, static_folder='ui')
CORS(app)

# Global state
state = {
    "status": "online",
    "model": "llama3",
    "voice_active": False,
    "history": []
}

OLLAMA_URL = "http://localhost:11434"

SYSTEM_PROMPT = """Sen MICRON adında bir kişisel yapay zeka asistanısın. Iron Man'in JARVIS'i gibisin.
Kısa, net ve etkili cevaplar ver. Türkçe konuş.

Kullanıcı bir şey açmak, çalıştırmak veya yapmak istediğinde, SADECE JSON döndür:
{
  "action": "open_web|open_app|run_command|answer|search",
  "target": "url veya uygulama adı veya komut",
  "response": "kullanıcıya kısa mesaj"
}

Bilgi sorusu ise:
{
  "action": "answer",
  "target": "",
  "response": "cevap metni"
}

Örnekler:
- "Google'ı aç" -> {"action":"open_web","target":"https://google.com","response":"Google açılıyor"}
- "VS Code'u aç" -> {"action":"open_app","target":"code","response":"VS Code başlatılıyor"}
- "Hava nasıl?" -> {"action":"search","target":"hava durumu bugün","response":"Hava durumunu arıyorum"}
- "Python nedir?" -> {"action":"answer","target":"","response":"Python açıklama..."}
"""

def ask_ollama(prompt, model=None):
    """Ollama'ya istek gönder"""
    model = model or state["model"]
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": f"SYSTEM: {SYSTEM_PROMPT}\n\nUSER: {prompt}\n\nASSISTANT:",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            return json.dumps({"action":"answer","target":"","response":"Ollama bağlantı hatası"})
    except requests.exceptions.ConnectionError:
        return json.dumps({"action":"answer","target":"","response":"Ollama çalışmıyor. 'ollama serve' komutunu çalıştırın."})
    except Exception as e:
        return json.dumps({"action":"answer","target":"","response":f"Hata: {str(e)}"})

def execute_action(action, target):
    """Komutu çalıştır"""
    os_type = platform.system().lower()
    
    if action == "open_web":
        url = target if target.startswith("http") else f"https://{target}"
        webbrowser.open(url)
        return True
    
    elif action == "open_app":
        try:
            if os_type == "darwin":
                subprocess.Popen(target, shell=True)
            elif os_type == "windows":
                subprocess.Popen(target, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(target, shell=True)
            return True
        except:
            return False
    
    elif action == "run_command":
        try:
            result = subprocess.run(target, shell=True, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except:
            return False
    
    elif action == "search":
        query = target.replace(" ", "+")
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return True
    
    return True

@app.route("/api/command", methods=["POST"])
def handle_command():
    data = request.json
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"error": "Boş komut"}), 400
    
    # Hızlı URL/site tanıma
    quick_sites = {
        "google": "https://google.com",
        "youtube": "https://youtube.com",
        "github": "https://github.com",
        "gmail": "https://gmail.com",
        "twitter": "https://twitter.com",
        "linkedin": "https://linkedin.com",
        "reddit": "https://reddit.com",
        "netflix": "https://netflix.com",
        "spotify": "https://open.spotify.com",
        "whatsapp": "https://web.whatsapp.com",
        "claude": "https://claude.ai",
        "chatgpt": "https://chat.openai.com",
        "instagram": "https://instagram.com",
    }
    
    text_lower = text.lower()
    
    # Hızlı site eşleştirme
    for site, url in quick_sites.items():
        if site in text_lower and any(kw in text_lower for kw in ["aç", "git", "açsın", "başlat", "open", "gir"]):
            execute_action("open_web", url)
            result = {
                "action": "open_web",
                "target": url,
                "response": f"{site.title()} açıldı! 🌐",
                "success": True,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            state["history"].append({"role": "user", "text": text, "time": result["timestamp"]})
            state["history"].append({"role": "micron", "text": result["response"], "time": result["timestamp"]})
            return jsonify(result)
    
    # VS Code / Cursor hızlı tanıma
    if any(kw in text_lower for kw in ["vscode", "vs code", "visual studio", "cursor"]):
        if any(kw in text_lower for kw in ["aç", "başlat", "open"]):
            app_cmd = "cursor" if "cursor" in text_lower else "code"
            
            # Proje yolu var mı?
            path_match = re.search(r'(?:ve\s+)?([~/].+?)\s*(?:proje|project|klasör|folder)?(?:\s*açsın|\s*aç)?$', text_lower)
            if path_match:
                app_cmd += f" {path_match.group(1)}"
            
            execute_action("open_app", app_cmd)
            result = {
                "action": "open_app",
                "target": app_cmd,
                "response": f"{'Cursor' if 'cursor' in text_lower else 'VS Code'} başlatılıyor! 💻",
                "success": True,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            state["history"].append({"role": "user", "text": text, "time": result["timestamp"]})
            state["history"].append({"role": "micron", "text": result["response"], "time": result["timestamp"]})
            return jsonify(result)
    
    # Ollama'ya sor
    llm_response = ask_ollama(text)
    
    # JSON parse
    action_data = {"action": "answer", "target": "", "response": llm_response}
    try:
        json_match = re.search(r'\{[^{}]*\}', llm_response, re.DOTALL)
        if json_match:
            action_data = json.loads(json_match.group())
    except:
        pass
    
    # Eylemi çalıştır
    if action_data.get("action") != "answer":
        execute_action(action_data.get("action", ""), action_data.get("target", ""))
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    result = {
        **action_data,
        "success": True,
        "timestamp": timestamp
    }
    
    state["history"].append({"role": "user", "text": text, "time": timestamp})
    state["history"].append({"role": "micron", "text": action_data.get("response", ""), "time": timestamp})
    
    return jsonify(result)

@app.route("/api/status", methods=["GET"])
def get_status():
    # Ollama kontrol
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])] if ollama_ok else []
    except:
        ollama_ok = False
        models = []
    
    return jsonify({
        "status": "online",
        "ollama": ollama_ok,
        "model": state["model"],
        "available_models": models,
        "voice": state["voice_active"],
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%d.%m.%Y")
    })

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(state["history"][-50:])

@app.route("/api/clear", methods=["POST"])
def clear_history():
    state["history"] = []
    return jsonify({"ok": True})

@app.route("/api/model", methods=["POST"])
def set_model():
    data = request.json
    state["model"] = data.get("model", "llama3")
    return jsonify({"model": state["model"]})

@app.route("/", methods=["GET"])
def index():
    return send_from_directory("ui", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("ui", filename)

if __name__ == "__main__":
    print("🤖 MICRON API Sunucusu başlatılıyor...")
    print("📡 http://localhost:5000 adresinde çalışıyor")
    app.run(host="0.0.0.0", port=5000, debug=False)
