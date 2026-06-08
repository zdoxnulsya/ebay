import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup

EBAY_URL = "https://www.ebay.com/sch/i.html?_sop=10&_from=R40&_nkw=ernie+ball+electric+guitar+strings&_sacat=0&_fcid=1"
STATE_FILE = "seen_listings.json"
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def fetch_listings():
    resp = requests.get(EBAY_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    listings = []
    for item in soup.select(".s-item"):
        title_el = item.select_one(".s-item__title")
        price_el = item.select_one(".s-item__price")
        link_el = item.select_one(".s-item__link")

        # Skip the phantom "Shop on eBay" placeholder item
        if not title_el or not link_el:
            continue
        title = title_el.get_text(strip=True)
        if title == "Shop on eBay":
            continue

        price = price_el.get_text(strip=True) if price_el else "N/A"
        url = link_el["href"].split("?")[0]  # strip tracking params

        # Use URL path as stable ID (item number is embedded in the URL)
        item_id = hashlib.md5(url.encode()).hexdigest()

        listings.append({"id": item_id, "title": title, "price": price, "url": url})

    return listings


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    requests.post(url, json=payload, timeout=10)


def main():
    seen = load_seen()
    listings = fetch_listings()

    new_listings = [l for l in listings if l["id"] not in seen]

    if new_listings:
        for l in new_listings:
            msg = (
                f'🎸 <b>New eBay Listing</b>\n\n'
                f'<b>{l["title"]}</b>\n'
                f'💰 {l["price"]}\n'
                f'🔗 <a href="{l["url"]}">View on eBay</a>'
            )
            send_telegram(msg)
            seen.add(l["id"])
        print(f"Sent {len(new_listings)} new listing(s).")
    else:
        print("No new listings found.")

    save_seen(seen)


if __name__ == "__main__":
    main()
