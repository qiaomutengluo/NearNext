import re
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (compatible; EventWorkflow/1.0)"}
r = requests.get("https://www.concordia.ca/events.html", headers=UA, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

for section in soup.select(".list-events"):
    print("SECTION:", section.get("class"))
    items = section.select(".c-event, .event, li, article, .item")
    print("  child tags:", {c.name: c.get("class") for c in section.find_all(recursive=False)[:5]})

# find h3 headers (event titles from markdown)
h3s = soup.select("h3")
print("h3 count:", len(h3s))
if h3s:
    print(h3s[0].prettify()[:500])
    parent = h3s[0].parent
    print("parent:", parent.name, parent.get("class"))
    print(parent.prettify()[:2000])

# look for structured event blocks
for div in soup.select("div[class*='event']"):
    cls = " ".join(div.get("class", []))
    if "list" not in cls and len(div.get_text(strip=True)) > 50:
        print("DIV", cls, "text len", len(div.get_text()))
        print(div.prettify()[:800])
        break
