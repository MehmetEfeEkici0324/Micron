"""
MICRON - API Sunucusu
Web arayuzu ile Python backend arasindaki kopru.
"""

import json
import os
import platform
import re
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
SKILLS_PATH = BASE_DIR / "skills" / "custom_skills.json"

DEFAULT_CONFIG = {
    "assistant_name": "MICRON",
    "model": "llama3",
    "ollama_url": "http://localhost:11434",
    "ollama_autostart": True,
    "language": "tr-TR",
    "wake_word": "micron",
    "voice_enabled": True,
    "voice_rate": 0.86,
    "voice_pitch": 0.72,
    "preferred_voice_keywords": ["male", "erkek", "tolga", "microsoft", "tr"],
    "speech_continuous": True,
    "speech_interim_results": True,
    "speech_max_alternatives": 3,
    "speech_command_without_wake_word": True,
    "server_host": "0.0.0.0",
    "server_port": 5000,
    "auto_start_browser": True,
    "default_browser": "chrome",
    "response_language": "tr-TR",
    "command_timeout_seconds": 30,
    "allow_shell_commands": True,
    "custom_sites": {},
    "custom_apps": {},
    "learned_commands": {},
    "project_roots": [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Documents"),
        str(Path.home() / "Desktop" / "Micron")
    ],
    "blocked_shell_patterns": [
        "rm -rf",
        "del /f",
        "format ",
        "shutdown",
        "reboot",
        "git reset --hard"
    ]
}


def deep_merge(defaults, current):
    merged = dict(defaults)
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_json(path, fallback):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
    except Exception as exc:
        print(f"Config okunamadi: {path} -> {exc}")
    return fallback


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_config():
    config = deep_merge(DEFAULT_CONFIG, load_json(CONFIG_PATH, {}))
    save_json(CONFIG_PATH, config)
    return config


config = load_config()
skills = load_json(SKILLS_PATH, {"web_sites": {}, "desktop_apps": {}, "custom_commands": {}})

app = Flask(__name__, static_folder="ui")
CORS(app)

state = {
    "status": "online",
    "model": config["model"],
    "voice_active": False,
    "history": [],
    "chat_messages": []
}

VALID_ACTIONS = {"open_web", "open_app", "open_folder", "open_terminal", "run_command", "search", "answer", "learn_command"}


def os_type():
    return platform.system().lower()


def windows_cmd(name):
    windows_map = {
        "chrome": "start chrome",
        "edge": "start msedge",
        "firefox": "start firefox",
        "terminal": "start wt",
        "cmd": "start cmd",
        "powershell": "start powershell",
        "notepad": "notepad",
        "calculator": "calc",
        "hesap makinesi": "calc",
        "dosya yoneticisi": "explorer .",
        "dosya yöneticisi": "explorer .",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "cursor": "cursor",
        "opencode": "opencode"
    }
    return windows_map.get(name)


def get_site_map():
    base = dict(skills.get("web_sites", {}))
    base.update(config.get("custom_sites", {}))
    return {normalize_key(k): v for k, v in base.items()}


def get_app_map():
    base = dict(skills.get("desktop_apps", {}))
    if os_type() == "windows":
        for name in ["chrome", "edge", "firefox", "terminal", "cmd", "powershell", "notepad", "calculator", "hesap makinesi", "dosya yöneticisi", "vscode", "vs code", "visual studio code", "cursor", "opencode"]:
            base[name] = windows_cmd(name) or base.get(name, name)
    base.update(config.get("custom_apps", {}))
    return {normalize_key(k): v for k, v in base.items()}


def get_custom_commands():
    return {normalize_key(k): v for k, v in skills.get("custom_commands", {}).items()}


def get_learned_commands():
    return {normalize_key(k): v for k, v in config.get("learned_commands", {}).items()}


def normalize_key(text):
    return (text or "").lower().replace("ı", "i").strip()


def normalize_text(text):
    text = normalize_key(text)
    replacements = {
        "googleyi": "google",
        "google'i": "google",
        "googleı": "google",
        "youtube'u": "youtube",
        "github'i": "github",
        "githubı": "github",
        "vscode'u": "vscode",
        "vs code'u": "vs code",
        "opencodu": "opencode",
        "open code": "opencode",
        "lo-fi": "lofi"
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


SYSTEM_PROMPT = """Sen MICRON adında kişisel bir yapay zeka asistanısın. Türkçe konuş.
Kullanıcının amacını anla ve yalnızca geçerli JSON döndür.

Eylem gerekiyorsa:
{"action":"open_web|open_app|open_folder|run_command|search|answer","target":"hedef","response":"kısa yanıt"}

Kurallar:
- Sadece JSON döndür, markdown kullanma.
- Site açma için open_web, uygulama açma için open_app, klasör açma için open_folder kullan.
- Bilgi sorularinda action answer olsun.
- Emin degilsen arama icin search kullan.
- Kısa ve net Türkçe yanıt ver.
- JSON dışında hiçbir açıklama yazma.
"""


def ensure_ollama_running():
    if not config.get("ollama_autostart", True):
        return
    try:
        requests.get(f"{config['ollama_url']}/api/tags", timeout=1.5)
    except Exception:
        try:
            subprocess.Popen("ollama serve", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def ask_ollama(prompt, model=None):
    model = model or state["model"]
    ensure_ollama_running()
    language = config.get("response_language") or config.get("language", "tr-TR")

    try:
        response = requests.post(
            f"{config['ollama_url']}/api/generate",
            json={
                "model": model,
                "prompt": f"SYSTEM: {SYSTEM_PROMPT}\nYanıt dili: {language}\n\nUSER: {prompt}\n\nASSISTANT:",
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 220
                }
            },
            timeout=35
        )
        if response.status_code == 200:
            return response.json().get("response", "")
        return json.dumps({"action": "answer", "target": "", "response": f"Ollama yanıt vermedi: HTTP {response.status_code}"})
    except requests.exceptions.ConnectionError:
        return json.dumps({"action": "answer", "target": "", "response": "Ollama çalışmıyor. Micron başlatırken 'ollama serve' otomatik deneniyor; olmazsa terminalden elle çalıştırın."})
    except Exception as exc:
        return json.dumps({"action": "answer", "target": "", "response": f"Ollama hatasi: {exc}"})


def ask_ollama_chat(prompt, model=None):
    model = model or state["model"]
    ensure_ollama_running()
    language = config.get("response_language") or config.get("language", "tr-TR")
    system_prompt = (
        "Sen MICRON adında kişisel bir yapay zeka asistanısın. "
        "Kullanıcıyla doğal, karşılıklı sohbet et. "
        "Komut çalıştırma JSON'u üretme; normal metin cevap ver. "
        f"Yanıt dili: {language}. Kısa, net ve Türkçe karakterleri doğru kullan."
    )
    messages = [{"role": "system", "content": system_prompt}, *state["chat_messages"][-12:], {"role": "user", "content": prompt}]

    try:
        response = requests.post(
            f"{config['ollama_url']}/api/chat",
            json={"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.6, "num_predict": 500}},
            timeout=45
        )
        if response.status_code == 200:
            answer = response.json().get("message", {}).get("content", "").strip()
            state["chat_messages"].append({"role": "user", "content": prompt})
            state["chat_messages"].append({"role": "assistant", "content": answer})
            state["chat_messages"] = state["chat_messages"][-24:]
            return answer or "Buradayım. Devam edebilirsin."
        return f"Ollama yanıt vermedi: HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Ollama çalışmıyor. Sohbet için Ollama servisinin açık olması gerekiyor."
    except Exception as exc:
        return f"Ollama sohbet hatası: {exc}"


def extract_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict) and parsed.get("action") in VALID_ACTIONS:
                if parsed.get("target") in ["hedef", "target", "url", ""] and parsed.get("action") not in ["answer"]:
                    return {"action": "answer", "target": "", "response": "Bu komutu net anlayamadım. Ne açmamı veya aramamı istediğini daha açık yazar mısın?"}
                return parsed
    except Exception:
        pass
    cleaned = re.sub(r"SYSTEM:.*?ASSISTANT:", "", text or "", flags=re.DOTALL).strip()
    if not cleaned or any(marker in cleaned.lower() for marker in ["open_web|open_app", "yalnizca gecerli json", "kullanicinin amacini"]):
        cleaned = "Bunu anlayamadım. Daha kısa bir komutla tekrar söyleyebilir misin?"
    return {"action": "answer", "target": "", "response": cleaned[:500]}


def is_shell_blocked(command):
    command_lower = normalize_text(command)
    return any(pattern in command_lower for pattern in config.get("blocked_shell_patterns", []))


def open_url(url):
    browser = normalize_key(config.get("default_browser", "chrome"))
    system = os_type()
    if system == "windows" and browser == "chrome":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "chrome", url], shell=False)
            return
        except Exception:
            pass
    if browser:
        try:
            webbrowser.get(browser).open(url)
            return
        except Exception:
            pass
    webbrowser.open(url)


def find_project_path(text):
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        return quoted.group(1)

    lowered = normalize_text(text)
    for root in config.get("project_roots", []):
        root_path = Path(os.path.expanduser(root))
        if not root_path.exists():
            continue
        for child in root_path.iterdir():
            if child.is_dir() and normalize_key(child.name) in lowered:
                return str(child)
    return ""


def parse_learn_command(text):
    lowered = normalize_text(text)
    if not any(marker in lowered for marker in ["komutunu sisteme ekle", "komut olarak ekle", "dediğimde", "dedigimde"]):
        return None

    patterns = [
        r"(?P<trigger>.+?)\s+komutunu\s+sisteme\s+ekle\s*[,;:]?\s*(?P<task>.+)",
        r"(?P<trigger>.+?)\s+komut\s+olarak\s+ekle\s*[,;:]?\s*(?P<task>.+)",
        r"(?P<trigger>.+?)\s+(?:dediğimde|dedigimde)\s+(?P<task>.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue
        trigger = cleanup_learned_trigger(match.group("trigger"))
        task = cleanup_learned_task(match.group("task"))
        if not trigger or not task:
            continue
        if trigger in ["bunu", "şunu", "sunu", "bu"]:
            return {"action": "answer", "target": "", "response": "Komut adını net söylemelisin. Örnek: 'ders modu komutunu sisteme ekle, YouTube lo-fi aç'."}

        command = parse_local_command(task, allow_learning=False) or extract_json(ask_ollama(task))
        if command.get("action") == "answer" and not command.get("target"):
            command = {"action": "search", "target": task, "response": f"{task} aranıyor."}

        config.setdefault("learned_commands", {})[trigger] = {
            "task": task,
            "command": command,
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        save_json(CONFIG_PATH, config)
        return {"action": "learn_command", "target": trigger, "response": f"'{trigger}' komutunu öğrendim. Bundan sonra bu komutu söylediğinde kayıtlı görevi çalıştıracağım."}

    return {"action": "answer", "target": "", "response": "Komutu kaydetmek için şu format daha iyi: 'komut adı komutunu sisteme ekle, yapılacak iş'."}


def youtube_search_url(query):
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def extract_youtube_query(text):
    query = normalize_text(text)
    query = re.sub(r"\b(youtube|yutub|you tube|aç|ac|başlat|baslat|git|videolarını|videolarini|videosunu|video|müzik|muzik)\b", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query


def looks_like_command(text):
    lowered = normalize_text(text)
    command_markers = [
        "aç", "ac", "başlat", "baslat", "çalıştır", "calistir", "gir", "ara", "search",
        "komutunu sisteme ekle", "komut olarak ekle", "dediğimde", "dedigimde",
        "klasör", "klasor", "dosya", "terminal", "opencode", "vscode", "cursor"
    ]
    return any(marker in lowered for marker in command_markers)


def cleanup_learned_trigger(text):
    text = normalize_text(text)
    text = re.sub(r"\b(micron|mikron|hey|lütfen|lutfen)\b", "", text).strip()
    return text.strip(" .,;:'\"")


def cleanup_learned_task(text):
    text = normalize_text(text)
    text = re.sub(r"^(ve\s+)?(bunu|şunu|sunu|bu)\s+", "", text).strip()
    return text.strip(" .,;:'\"")


def parse_local_command(text, allow_learning=True):
    lowered = normalize_text(text)
    site_map = get_site_map()
    app_map = get_app_map()
    custom_commands = get_custom_commands()
    open_words = ["ac", "aç", "baslat", "başlat", "calistir", "çalıştır", "gir", "open"]

    if allow_learning:
        learned = parse_learn_command(text)
        if learned:
            return learned

    for name, learned in get_learned_commands().items():
        if lowered == name or name in lowered:
            command = dict(learned.get("command", {}))
            command["response"] = command.get("response") or f"{name} komutu çalıştırılıyor."
            command["learned_trigger"] = name
            return command

    for name, command in custom_commands.items():
        if name in lowered:
            return {"action": "run_command", "target": command, "response": f"{name} komutu çalıştırılıyor."}

    if any(word in lowered for word in ["saat kac", "saat kaç"]):
        return {"action": "answer", "target": "", "response": datetime.now().strftime("Saat %H:%M")}

    if any(word in lowered for word in ["bugun tarih", "bugün tarih", "tarih ne"]):
        return {"action": "answer", "target": "", "response": datetime.now().strftime("Bugün %d.%m.%Y")}

    if any(word in lowered for word in ["ara", "search"]):
        query = re.sub(r"\b(google'?da|googlede|ara|search|internette)\b", "", lowered).strip()
        if query:
            return {"action": "search", "target": query, "response": f"{query} aranıyor."}

    if any(word in lowered for word in open_words):
        if "youtube" in lowered or "yutub" in lowered or "you tube" in lowered:
            query = extract_youtube_query(lowered)
            if query:
                return {"action": "open_web", "target": youtube_search_url(query), "response": f"YouTube'da {query} açılıyor."}

        for name, url in site_map.items():
            if name in lowered:
                return {"action": "open_web", "target": url, "response": f"{name.title()} açılıyor."}

        for name, command in app_map.items():
            if name in lowered:
                project_path = find_project_path(text)
                if project_path and name == "opencode":
                    return {"action": "open_terminal", "target": f"{project_path}||opencode", "response": "Opencode proje klasöründe başlatılıyor."}
                if project_path and name in ["vscode", "vs code", "visual studio code", "cursor"]:
                    command = f'{command} "{project_path}"'
                return {"action": "open_app", "target": command, "response": f"{name.title()} başlatılıyor."}

        folder_match = re.search(r"(?:klasor|klasör|folder|dizin)\s+(.+)", lowered)
        if folder_match:
            return {"action": "open_folder", "target": folder_match.group(1).strip(), "response": "Klasör açılıyor."}

        url_match = re.search(r"((?:https?://)?[a-z0-9-]+\.[a-z]{2,}(?:/\S*)?)", lowered)
        if url_match:
            target = url_match.group(1)
            return {"action": "open_web", "target": target, "response": f"{target} açılıyor."}

    return None


def execute_action(action, target):
    target = target or ""
    system = os_type()

    try:
        if action == "open_web":
            url = target if target.startswith("http") else f"https://{target}"
            open_url(url)
            return True, url

        if action == "search":
            query = quote_plus(target)
            url = f"https://www.google.com/search?q={query}"
            open_url(url)
            return True, url

        if action == "open_folder":
            path = os.path.expanduser(target.strip('"'))
            if system == "darwin":
                subprocess.Popen(["open", path])
            elif system == "windows":
                subprocess.Popen(["explorer", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return True, path

        if action == "open_app":
            flags = subprocess.CREATE_NEW_CONSOLE if system == "windows" else 0
            subprocess.Popen(target, shell=True, creationflags=flags)
            return True, target

        if action == "open_terminal":
            cwd, command = target.split("||", 1)
            cwd = os.path.expanduser(cwd)
            if system == "windows":
                subprocess.Popen(["cmd", "/k", command], cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(command, shell=True, cwd=cwd)
            return True, f"{command} @ {cwd}"

        if action == "run_command":
            if not config.get("allow_shell_commands", False):
                return False, "Shell komutları config tarafından kapalı."
            if is_shell_blocked(target):
                return False, "Bu komut güvenlik nedeniyle engellendi."
            result = subprocess.run(
                target,
                shell=True,
                capture_output=True,
                text=True,
                timeout=int(config.get("command_timeout_seconds", 30))
            )
            output = (result.stdout or result.stderr or "Komut tamamlandı.").strip()
            return result.returncode == 0, output[:1000]
    except Exception as exc:
        return False, str(exc)

    return True, ""


def add_history(role, text, timestamp):
    state["history"].append({"role": role, "text": text, "time": timestamp})
    state["history"] = state["history"][-100:]


@app.route("/api/command", methods=["POST"])
def handle_command():
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Boş komut"}), 400

    action_data = parse_local_command(text)
    if not action_data:
        if looks_like_command(text):
            action_data = extract_json(ask_ollama(text))
        else:
            action_data = {"action": "answer", "target": "", "response": ask_ollama_chat(text)}

    success = True
    execution_result = ""
    if action_data.get("action") not in ["answer", "learn_command"]:
        success, execution_result = execute_action(action_data.get("action", ""), action_data.get("target", ""))

    timestamp = datetime.now().strftime("%H:%M:%S")
    if not success:
        action_data["response"] = f"Komut tamamlanamadı: {execution_result}"

    result = {
        **action_data,
        "success": success,
        "execution_result": execution_result,
        "timestamp": timestamp
    }

    add_history("user", text, timestamp)
    add_history("micron", action_data.get("response", ""), timestamp)
    return jsonify(result)


@app.route("/api/status", methods=["GET"])
def get_status():
    ensure_ollama_running()
    try:
        response = requests.get(f"{config['ollama_url']}/api/tags", timeout=3)
        ollama_ok = response.status_code == 200
        models = [model["name"] for model in response.json().get("models", [])] if ollama_ok else []
    except Exception:
        ollama_ok = False
        models = []

    return jsonify({
        "status": "online",
        "ollama": ollama_ok,
        "ollama_url": config["ollama_url"],
        "model": state["model"],
        "available_models": models,
        "voice": state["voice_active"],
        "config": public_config(),
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%d.%m.%Y")
    })


def public_config():
    allowed = [
        "assistant_name",
        "wake_word",
        "language",
        "voice_enabled",
        "voice_rate",
        "voice_pitch",
        "preferred_voice_keywords",
        "response_language",
        "speech_continuous",
        "speech_interim_results",
        "speech_max_alternatives",
        "speech_command_without_wake_word"
    ]
    return {key: config.get(key) for key in allowed}


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(public_config())


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(state["history"][-50:])


@app.route("/api/clear", methods=["POST"])
def clear_history():
    state["history"] = []
    return jsonify({"ok": True})


@app.route("/api/model", methods=["POST"])
def set_model():
    data = request.json or {}
    state["model"] = data.get("model", config.get("model", "llama3"))
    config["model"] = state["model"]
    save_json(CONFIG_PATH, config)
    return jsonify({"model": state["model"]})


@app.route("/", methods=["GET"])
def index():
    return send_from_directory("ui", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("ui", filename)


if __name__ == "__main__":
    ensure_ollama_running()
    print("MICRON API Sunucusu başlatılıyor...")
    print(f"Ollama: {config['ollama_url']}")
    print(f"Model: {state['model']}")
    print(f"Adres: http://localhost:{config['server_port']}")
    app.run(host=config.get("server_host", "0.0.0.0"), port=int(config.get("server_port", 5000)), debug=False)
