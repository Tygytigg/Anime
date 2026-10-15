import json
import os
import re
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# ====== CONFIG ======
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906081106:AAGDxZeFio73Fp6lU-gFxNRLgpu_3Yg1xIQ")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6402561515")

DOMAINE = "https://anime-sama.to"  
INTERVALLE_MIN = 30                

ANIMES = {
    "The ramparts of ice": "/catalogue/the-ramparts-of-ice/saison2/vf/", # Espace corrigé ici !
    "Tokyo Revengers": "/catalogue/tokyo-revengers/saison4/vostfr/",
    "Dragon Ball Daima": "/catalogue/dragon-ball-daima/saison1/vostfr/",
}

ETAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etat_animesama.json")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ====== FAUX SERVEUR POUR RENDER (GRATUIT) ======
class FakeWebService(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot en cours d'execution...")

def lancer_serveur_web():
    # Render donne le port via la variable PORT, sinon 10000 par défaut
    port = int(os.environ.get("PORT", 10000))
    serveur = HTTPServer(("0.0.0.0", port), FakeWebService)
    print(f"Faux serveur actif sur le port {port}")
    serveur.serve_forever()
# ================================================

def notifier(texte):
    r = requests.post(
        f"https://telegram.org{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": texte},
        timeout=15,
    )
    r.raise_for_status()

def compter_episodes(chemin):
    r = requests.get(DOMAINE + chemin + "episodes.js", headers=HEADERS, timeout=20)
    r.raise_for_status()
    tableaux = re.findall(r"eps\d*\s*=\s*\[(.*?)\]", r.text, re.S)
    return max((len(re.findall(r"https?://", t)) for t in tableaux), default=0)

def charger_etat():
    if os.path.exists(ETAT):
        with open(ETAT, encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauver_etat(etat):
    with open(ETAT, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=2)

def verifier():
    print("--- Verification des episodes ---")
    etat = charger_etat()
    for nom, chemin in ANIMES.items():
        try:
            n = compter_episodes(chemin)
            print(f"{nom} : {n} épisode(s) en ligne")
            if n == 0:
                continue
            if nom not in etat:
                etat[nom] = n  
            elif n > etat[nom]:
                notifier(f"🔔 {nom} : épisode {n} dispo sur anime-sama\n{DOMAINE + chemin}")
                etat[nom] = n
        except Exception as e:
            print(f"{nom} -> erreur : {e}")
    sauver_etat(etat)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        notifier("test")
        print("Message de test envoyé")
        sys.exit()

    # 1. On lance le serveur web dans un fil secondaire pour satisfaire Render
    t = threading.Thread(target=lancer_serveur_web, daemon=True)
    t.start()

    # 2. On lance la boucle de vérification infinie sur le fil principal
    while True:
        verifier()
        if INTERVALLE_MIN <= 0:
            break
        time.sleep(INTERVALLE_MIN * 60)
