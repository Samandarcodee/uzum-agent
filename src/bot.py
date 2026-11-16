import os, time, json, logging
import requests
from uzum import UzumClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")


def load_env(path=os.path.join(os.path.dirname(__file__), "..", ".env")):
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED = {int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()}
API = f"https://api.telegram.org/bot{TOKEN}"
uzum = UzumClient(os.environ["UZUM_API_KEY"])

HELP = (
    "Uzum Seller bot\n\n"
    "/shops - do'konlar\n"
    "/products - mahsulotlar\n"
    "/orders [status] - FBS buyurtmalar (masalan: /orders CREATED)\n"
    "/count - buyurtmalar soni\n"
    "/stocks - FBS qoldiqlar\n"
    "/id - sizning Telegram ID"
)


def send(chat_id, text):
    for i in range(0, len(text), 4000):
        requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text[i:i + 4000]}, timeout=30)


def shops_list():
    data = uzum.shops()
    return data.get("payload", data) if isinstance(data, dict) else data


def shop_ids():
    return [s["id"] for s in shops_list()]


def handle(cmd, args, chat_id):
    if cmd in ("/start", "/help"):
        return HELP
    if cmd == "/id":
        return f"ID: {chat_id}"
    if cmd == "/shops":
        return "\n".join(f"{s['id']} - {s.get('name')}" for s in shops_list()) or "Do'kon yo'q"
    if cmd == "/products":
        out = []
        for sid in shop_ids():
            try:
                d = uzum.products(sid).get("payload") or {}
            except Exception as e:
                out.append(f"[{sid}] xato: {e}")
                continue
            for p in d.get("productList", [])[:20]:
                out.append(f"[{sid}] {p.get('title')} | qoldiq: {p.get('quantityActive', '?')} | narx: {p.get('price', '?')}")
        return "\n".join(out) or "Mahsulot yo'q"
    if cmd == "/orders":
        status = args[0].upper() if args else None
        out = []
        for sid in shop_ids():
            try:
                d = uzum.orders([sid], status).get("payload") or {}
            except Exception as e:
                out.append(f"[{sid}] ruxsat yo'q/xato: {str(e)[:80]}")
                continue
            for o in d.get("orders", []):
                items = ", ".join(f"{i.get('skuTitle')} x{i.get('amount')}" for i in o.get("orderItems", []))
                out.append(f"[{sid}] #{o.get('id')} {o.get('status')} | {o.get('price')} so'm | {items}")
        return "\n".join(out) or "Buyurtma yo'q"
    if cmd == "/count":
        out = []
        for sid in shop_ids():
            try:
                out.append(f"[{sid}] {json.dumps(uzum.order_count([sid]), ensure_ascii=False)}")
            except Exception as e:
                out.append(f"[{sid}] ruxsat yo'q/xato: {str(e)[:80]}")
        return "\n".join(out)
    if cmd == "/stocks":
        d = uzum.stocks().get("payload", {})
        out = [f"{s.get('productTitle')} / {s.get('skuTitle')}: {s.get('amount')}" for s in d.get("skuAmountList", [])[:50]]
        return "\n".join(out) or "Ma'lumot yo'q"
    return "Noma'lum buyruq. /help"


def main():
    offset = None
    log.info("Bot ishga tushdi")
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=60).json()
        except Exception as e:
            log.warning("poll error: %s", e); time.sleep(3); continue
        for u in r.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message")
            if not m or "text" not in m:
                continue
            chat_id = m["chat"]["id"]
            parts = m["text"].split()
            cmd, args = parts[0].split("@")[0].lower(), parts[1:]
            if ALLOWED and m["from"]["id"] not in ALLOWED and cmd != "/id":
                send(chat_id, "Ruxsat yo'q"); continue
            try:
                send(chat_id, handle(cmd, args, chat_id))
            except Exception as e:
                log.exception("handler")
                send(chat_id, f"Xato: {e}")


if __name__ == "__main__":
    main()
