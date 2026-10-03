"""Drive the console with a scripted scenario and capture screenshots + a JSON trace."""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(ROOT, "results", "demo_console.db")
if os.path.exists(DB): os.remove(DB)
SCENARIO = [
    "कोथरूडमध्ये पौड फाट्याजवळ रस्त्यावर मोठे खड्डे पडले आहेत",
    "कोथरूड पौड फाटा चौकात रस्त्यावर खूप मोठे खड्डे पडलेत, गाड्या आदळतात",
    "मुंढवा मध्ये चेंबरचं झाकण तुटलंय, उघडं आहे, कोणी पडू शकतं",
    "कोथरूडमध्ये पौड फाट्याजवळ रस्त्यावर मोठे खड्डे आहेत, कोणी लक्ष देत नाही",
    "वडगाव मध्ये तीन दिवसांपासून नळाला पाणी येत नाही",
    "kachra gadi 5 divas zale aali nahi, khup vaas yetoy",
    "Baner मध्ये street light बंद आहे",
]
env = dict(os.environ, NAGARVANI_DB=DB, PORT="5057")
srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "app", "app.py")], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(6)
trace = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1100, "height": 760}, device_scale_factor=2)
        for i, s in enumerate(SCENARIO, 1):
            pg.goto("http://127.0.0.1:5057/")
            pg.fill("textarea", s); pg.click("button"); pg.wait_for_load_state()
            card = pg.locator(".card").nth(1)
            trace.append(dict(step=i, text=s, card=card.inner_text()))
            if i in (3, 4, 5):
                pg.screenshot(path=os.path.join(ROOT, "results", "figures", f"screen_step{i}.png"), full_page=True)
        pg.goto("http://127.0.0.1:5057/queues")
        pg.screenshot(path=os.path.join(ROOT, "results", "figures", "screen_queues.png"), full_page=True)
        b.close()
finally:
    srv.terminate()
json.dump(trace, open(os.path.join(ROOT, "results", "demo_trace.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for t in trace:
    print(t["step"], t["card"].replace("\n", " | ")[:400]); print()
