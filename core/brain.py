"""
MICRON - Kişisel Yapay Zeka Asistanı
Ana Beyin Modülü
"""

import subprocess
import webbrowser
import os
import sys
import json
import re
import platform
import time
import threading
from datetime import datetime


class MicronBrain:
    def __init__(self, ollama_model="llama3"):
        self.model = ollama_model
        self.os_type = platform.system().lower()
        self.conversation_history = []
        self.skills = self._load_skills()
        
        # Uygulama -> komut eşleştirmeleri
        self.app_map = {
            "google": "https://google.com",
            "youtube": "https://youtube.com",
            "github": "https://github.com",
            "gmail": "https://gmail.com",
            "whatsapp": "https://web.whatsapp.com",
            "twitter": "https://twitter.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "netflix": "https://netflix.com",
            "spotify": "https://open.spotify.com",
            "chatgpt": "https://chat.openai.com",
            "claude": "https://claude.ai",
        }
        
        self.desktop_apps = {
            "vscode": self._get_vscode_cmd(),
            "vs code": self._get_vscode_cmd(),
            "visual studio code": self._get_vscode_cmd(),
            "chrome": self._get_chrome_cmd(),
            "firefox": "firefox",
            "terminal": self._get_terminal_cmd(),
            "notepad": "notepad" if self.os_type == "windows" else "gedit",
            "calculator": self._get_calc_cmd(),
            "file manager": self._get_file_manager_cmd(),
            "cursor": "cursor",
        }
    
    def _get_vscode_cmd(self):
        return "code" if self.os_type != "windows" else "code.cmd"
    
    def _get_chrome_cmd(self):
        if self.os_type == "darwin":
            return "open -a 'Google Chrome'"
        elif self.os_type == "windows":
            return "start chrome"
        return "google-chrome"
    
    def _get_terminal_cmd(self):
        if self.os_type == "darwin":
            return "open -a Terminal"
        elif self.os_type == "windows":
            return "start cmd"
        return "x-terminal-emulator"
    
    def _get_calc_cmd(self):
        if self.os_type == "darwin":
            return "open -a Calculator"
        elif self.os_type == "windows":
            return "calc"
        return "gnome-calculator"
    
    def _get_file_manager_cmd(self):
        if self.os_type == "darwin":
            return "open ."
        elif self.os_type == "windows":
            return "explorer ."
        return "nautilus ."
    
    def _load_skills(self):
        skills_file = os.path.join(os.path.dirname(__file__), "..", "skills", "custom_skills.json")
        if os.path.exists(skills_file):
            with open(skills_file) as f:
                return json.load(f)
        return {}
    
    def ask_ollama(self, prompt, system_prompt=None):
        """Ollama LLM'e sor"""
        import requests
        
        if system_prompt is None:
            system_prompt = """Sen MICRON adında bir kişisel yapay zeka asistanısın. 
            Iron Man'in JARVIS'i gibi akıllı, hızlı ve yardımseversin.
            Türkçe konuşuyorsun. Komutları analiz edip ne yapılması gerektiğini söyle.
            Eğer bir uygulama açılması, web sitesi ziyaret edilmesi, dosya işlemi veya 
            sistem komutu gerekiyorsa, bunu JSON formatında belirt:
            {"action": "open_web|open_app|run_command|code_task|answer", 
             "target": "hedef_url_veya_uygulama", 
             "details": "ek bilgi",
             "response": "kullanıcıya söylenecek mesaj"}"""
        
        self.conversation_history.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        *self.conversation_history
                    ],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result["message"]["content"]
                self.conversation_history.append({"role": "assistant", "content": message})
                return message
            else:
                return json.dumps({"action": "answer", "response": "Ollama bağlantısı kurulamadı.", "target": "", "details": ""})
        except Exception as e:
            return json.dumps({"action": "answer", "response": f"Hata: {str(e)}", "target": "", "details": ""})
    
    def parse_command(self, text):
        """Komutu analiz et ve ne yapılacağını belirle"""
        text_lower = text.lower().strip()
        
        # Doğrudan uygulama/site açma komutları
        open_patterns = [
            r"(aç|başlat|çalıştır|git|yükle)\s+(.+)",
            r"(.+)\s+(aç|başlat|çalıştır)",
            r"open\s+(.+)",
        ]
        
        for pattern in open_patterns:
            match = re.search(pattern, text_lower)
            if match:
                target = match.group(2) if match.lastindex >= 2 else match.group(1)
                target = target.strip()
                
                # Web sitesi mi?
                for site_name, url in self.app_map.items():
                    if site_name in target:
                        return {"action": "open_web", "target": url, "details": site_name, "response": f"{site_name.title()} açılıyor..."}
                
                # Masaüstü uygulama mı?
                for app_name, app_cmd in self.desktop_apps.items():
                    if app_name in target:
                        return {"action": "open_app", "target": app_cmd, "details": app_name, "response": f"{app_name.title()} açılıyor..."}
                
                # URL mi?
                if target.startswith("http") or "." in target:
                    return {"action": "open_web", "target": target if target.startswith("http") else f"https://{target}", "details": target, "response": f"{target} açılıyor..."}
        
        # Dosya yolu açma
        if any(keyword in text_lower for keyword in ["klasör", "dosya", "dizin", "folder"]):
            path_match = re.search(r'["\']?([/\\~].+?)["\']?\s*(?:aç|git|klasör)?$', text)
            if path_match:
                return {"action": "open_folder", "target": path_match.group(1), "details": "", "response": f"Klasör açılıyor..."}
        
        # Ollama'ya sor (karmaşık komutlar için)
        llm_response = self.ask_ollama(text)
        
        # JSON parse dene
        try:
            # JSON bloğu bul
            json_match = re.search(r'\{.*?\}', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"action": "answer", "response": llm_response, "target": "", "details": ""}
    
    def execute(self, command_result):
        """Komutu çalıştır"""
        action = command_result.get("action", "answer")
        target = command_result.get("target", "")
        details = command_result.get("details", "")
        
        if action == "open_web":
            webbrowser.open(target)
            return True, f"✅ {target} tarayıcıda açıldı"
        
        elif action == "open_app":
            try:
                if self.os_type == "darwin":
                    subprocess.Popen(target, shell=True)
                elif self.os_type == "windows":
                    subprocess.Popen(target, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(target, shell=True)
                return True, f"✅ {details} açıldı"
            except Exception as e:
                return False, f"❌ Uygulama açılamadı: {e}"
        
        elif action == "open_folder":
            try:
                path = os.path.expanduser(target)
                if self.os_type == "darwin":
                    subprocess.Popen(["open", path])
                elif self.os_type == "windows":
                    subprocess.Popen(["explorer", path])
                else:
                    subprocess.Popen(["xdg-open", path])
                return True, f"✅ {path} açıldı"
            except Exception as e:
                return False, f"❌ Klasör açılamadı: {e}"
        
        elif action == "run_command":
            try:
                result = subprocess.run(target, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout or result.stderr
                return True, f"✅ Komut çalıştırıldı:\n{output}"
            except Exception as e:
                return False, f"❌ Hata: {e}"
        
        elif action == "code_task":
            # VS Code ile proje açma
            project_path = os.path.expanduser(target) if target else "."
            try:
                subprocess.Popen(["code", project_path])
                return True, f"✅ VS Code'da {project_path} açıldı"
            except:
                return False, "❌ VS Code bulunamadı"
        
        return True, command_result.get("response", "Anlaşıldı.")
    
    def process(self, text):
        """Ana işleme fonksiyonu"""
        print(f"\n🧠 MICRON: '{text}' işleniyor...")
        
        command = self.parse_command(text)
        success, result_msg = self.execute(command)
        
        response = command.get("response", result_msg)
        
        return {
            "success": success,
            "action": command.get("action"),
            "message": response,
            "result": result_msg,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    brain = MicronBrain()
    print("MICRON Brain test...")
    result = brain.process("Google'ı aç")
    print(result)
