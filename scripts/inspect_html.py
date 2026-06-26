"""One-off HTML inspection script."""
import re
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (compatible; EventWorkflow/1.0)"}

print("=== McGill ===")
r = requests.get(
    "https://www.mcgill.ca/channels/section/all/channel_event",
    headers=UA,
    timeout=30,
)
print("status", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")
for sel in [".views-row", "article", ".node--type-channel-event", ".channel-event"]:
    els = soup.select(sel)
    print(f"{sel}: {len(els)}")
rows = soup.select(".views-row")
if rows:
    print(rows[0].prettify()[:2500])

print("\n=== Concordia ===")
r2 = requests.get("https://www.concordia.ca/events.html", headers=UA, timeout=30)
print("status", r2.status_code)
soup2 = BeautifulSoup(r2.text, "html.parser")
for sel in [
    ".c-events-list__item",
    ".event-item",
    "article.event",
    ".c-event",
    "[class*='event']",
]:
    els = soup2.select(sel)
    if els:
        print(f"{sel}: {len(els)}")
# find event container pattern
for tag in soup2.find_all(class_=re.compile(r"event", re.I))[:3]:
    print("class:", tag.get("class"), tag.name)
