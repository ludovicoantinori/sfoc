"""Genera una pagina con anteprima (titolo, descrizione, immagine) per ogni atto della Gazzetta Ufficiale.
WhatsApp e gli altri non leggono la parte del link dopo '#', quindi ogni atto ha il suo indirizzo: sfoc.it/gu/<id>/
La pagina mostra l'anteprima ai bot e porta subito le persone all'atto sul sito."""
import json, os, re, sys, shutil, hashlib, html, urllib.request
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "gu")
SITE = "https://sfoc.it"
KINDS = {"comunicato": "Comunicato", "avviso": "Avviso", "scadenza": "Scadenza", "bilancio": "Bilancio", "documento": "Documento"}
MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
HOT, BLK = (255, 43, 28), (10, 10, 10)

def fetch():
    if len(sys.argv) > 1:
        return json.load(open(sys.argv[1]))
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    url = re.search(r"https://[a-z0-9]+\.supabase\.co", src).group(0)
    key = re.search(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", src).group(0)
    req = urllib.request.Request(url + "/rest/v1/rpc/ve_news_list", data=b"{}", method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def day(t):
    d = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=1)))
    return f"{d.day} {MESI[d.month-1]} {d.year}"

F = lambda name, size: ImageFont.truetype(os.path.join(HERE, name), size)

def wrap(draw, text, font, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while draw.textlength(lines[-1] + "…", font=font) > width and " " in lines[-1]:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    return lines

def image(x, n, path):
    W, H, M = 1200, 630, 72
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    logo = Image.open(os.path.join(ROOT, "logo.png")).convert("RGBA").resize((62, 62), Image.LANCZOS)
    im.paste(logo, (M, 50), logo)
    d.text((M + 76, 54), "GAZZETTA UFFICIALE", font=F("inter-800.woff", 30), fill=BLK)
    d.text((M + 76, 88), "del Comitato Organizzativo dello Sfo", font=F("serif-italic.woff", 26), fill=HOT)
    d.rectangle((M, 134, W - M, 138), fill=BLK); d.rectangle((M, 143, W - M, 145), fill=BLK)
    tag = KINDS.get(x.get("kind"), "Comunicato").upper(); tf = F("inter-800.woff", 22)
    tw = d.textlength(tag, font=tf)
    d.rectangle((M, 172, M + tw + 28, 210), fill=HOT if x.get("kind") in ("scadenza", "avviso") else BLK)
    d.text((M + 14, 179), tag, font=tf, fill="white")
    d.text((M + tw + 46, 179), f"N. {n}  ·  {day(x['at']).upper()}", font=F("inter-700.woff", 22), fill=(110, 110, 110))
    title = x["title"].upper()
    for size in (84, 74, 64, 56, 50):
        tf = F("inter-800.woff", size); lines = wrap(d, title, tf, W - 2 * M, 3)
        if len(lines) <= 3 and not lines[-1].endswith("…") or size == 50: break
    y = 240
    for ln in lines:
        d.text((M - 3, y), ln, font=tf, fill=BLK); y += int(size * 0.98)
    body = re.sub(r"\s+", " ", x.get("body") or "").strip()
    if body and len(lines) < 3:
        bf = F("serif-italic.woff", 34); y += 14
        for ln in wrap(d, body, bf, W - 2 * M, 3 - len(lines) + (1 if len(lines) == 1 else 0)):
            if y > H - 140: break
            d.text((M, y), ln, font=bf, fill=(70, 70, 70)); y += 42
    docs = len(x.get("docs") or [])
    foot = F("inter-800.woff", 26)
    d.rectangle((M, H - 92, W - M, H - 90), fill=BLK)
    d.text((M, H - 70), "sfoc.it", font=foot, fill=BLK)
    if docs:
        t = f"+ {docs} ALLEGAT{'O' if docs == 1 else 'I'}"
        w = d.textlength(t, font=foot); d.rectangle((W - M - w - 32, H - 78, W - M, H - 30), fill=HOT)
        d.text((W - M - w - 16, H - 70), t, font=foot, fill="white")
    else:
        t = "Tocca per leggere"; w = d.textlength(t, font=F("serif-italic.woff", 30))
        d.text((W - M - w, H - 72), t, font=F("serif-italic.woff", 30), fill=HOT)
    im.save(path, optimize=True)

PAGE = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Gazzetta Ufficiale VE2027</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Gazzetta Ufficiale del COS">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.png">
<meta http-equiv="refresh" content="0;url=/#gu-{id}">
<script>location.replace("/#gu-{id}")</script>
<style>body{{margin:0;font:16px/1.4 Helvetica,Arial,sans-serif;display:grid;place-items:center;min-height:100vh}}a{{color:#ff2b1c}}</style>
</head><body><p>Apro l'atto… <a href="/#gu-{id}">Se non succede nulla, tocca qui.</a></p></body></html>
"""

def main():
    news = fetch()
    order = sorted(news, key=lambda x: x["at"])
    nums = {x["id"]: i + 1 for i, x in enumerate(order)}
    os.makedirs(OUT, exist_ok=True)
    keep = set()
    for x in news:
        i = x["id"]; keep.add(str(i)); n = nums[i]; folder = os.path.join(OUT, str(i)); os.makedirs(folder, exist_ok=True)
        sig = hashlib.sha1(json.dumps([x["title"], x["body"], x["kind"], x["at"], n, len(x.get("docs") or [])], ensure_ascii=False).encode()).hexdigest()[:10]
        stamp = os.path.join(folder, ".sig")
        if not (os.path.exists(stamp) and open(stamp).read() == sig):
            image(x, n, os.path.join(folder, "og.png"))
            open(stamp, "w").write(sig)
        body = re.sub(r"\s+", " ", x.get("body") or "").strip()
        docs = len(x.get("docs") or [])
        desc = f"Gazzetta Ufficiale n. {n}, {day(x['at'])}. " + (body[:150] + ("…" if len(body) > 150 else "") if body else "") + (f" {docs} allegat{'o' if docs == 1 else 'i'}." if docs else "")
        page = PAGE.format(title=html.escape(x["title"]), desc=html.escape(desc.strip()), url=f"{SITE}/gu/{i}/", img=f"{SITE}/gu/{i}/og.png?v={sig}", id=i)
        open(os.path.join(folder, "index.html"), "w", encoding="utf-8").write(page)
    for name in os.listdir(OUT):
        if name not in keep and os.path.isdir(os.path.join(OUT, name)):
            shutil.rmtree(os.path.join(OUT, name))
    open(os.path.join(OUT, ".keep"), "w").write("")
    print(f"{len(news)} atti, anteprime aggiornate")

main()
