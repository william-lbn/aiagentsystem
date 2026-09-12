from html.parser import HTMLParser
from pathlib import Path


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


h = Links()
h.feed(Path("production/agentops_service/data/demo_page.html").read_text())
print({"links": h.links, "decision": "click /runbooks/payments when task mentions payments"})
