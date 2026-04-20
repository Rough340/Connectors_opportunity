from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "connectorsATS_opportunities_dashboard.html"
CACHE_FILE = ROOT / "connectorsATS_live_feed.json"
PORT = 8765
CACHE_TTL_SECONDS = 300


SCRAPE_TARGETS: list[dict[str, Any]] = [
    {
        "id": 4101,
        "name": "Google for Startups Cloud Program",
        "type": "infra",
        "amount": "Up to $200K",
        "amountText": "Up to 200K USD",
        "amountNote": "$350K for AI startups",
        "desc": "Google Cloud program support for early startups with a higher upside if the startup qualifies as AI-first.",
        "tags": ["Official source", "Cloud credits", "Startup program"],
        "eligibility": "easy",
        "eligLabel": "Apply now",
        "fit": "Immediate",
        "signal": {"speed": "Fast", "leverage": "Very high", "friction": "Low"},
        "details": {
            "benefit": "Google publicly describes cloud, product, and mentor support with a larger allowance for AI startups.",
            "eligibility": ["Early-stage startup", "Working product helps", "AI startups may qualify for a higher tier"],
            "docs": ["Founder profile", "Product summary", "Website or MVP link"],
            "how": "Apply through the official Cloud Program page with a concise product summary and a live link.",
            "tip": "If AI-assisted matching is part of ConnectorsATS, mention that explicitly.",
            "url": "https://startup.google.com/cloud/",
            "sources": [{"label": "Official program page", "url": "https://startup.google.com/cloud/"}],
        },
        "checks": [
            r"up to \$200,000",
            r"up to \$350,000 for AI startups",
        ],
    },
    {
        "id": 4102,
        "name": "Microsoft for Startups",
        "type": "infra",
        "amount": "$5K+",
        "amountText": "5K plus",
        "amountNote": "Open offer now, more via investor path",
        "desc": "Microsoft's startup stack combines open Azure credits with larger investor-network benefits.",
        "tags": ["Official source", "Azure", "AI tools"],
        "eligibility": "easy",
        "eligLabel": "Apply now",
        "fit": "Immediate",
        "signal": {"speed": "Fast", "leverage": "High", "friction": "Low"},
        "details": {
            "benefit": "Microsoft Learn describes an open startup offer and Microsoft markets larger benefits through its investor-linked startup path.",
            "eligibility": ["Software-based startup", "Open to all startups for the base offer", "Enhanced benefits depend on investor-network access"],
            "docs": ["Startup profile", "Product description", "Team profile"],
            "how": "Start with the open Microsoft startup offer, then revisit upgraded benefits if an investor or accelerator referral becomes available.",
            "tip": "This works well as infrastructure plus productivity stack, not just credits.",
            "url": "https://www.microsoft.com/en-us/startups",
            "sources": [
                {"label": "Microsoft for Startups", "url": "https://www.microsoft.com/en-us/startups"},
                {"label": "Microsoft Learn overview", "url": "https://learn.microsoft.com/en-us/startups/microsoft-for-startups/overview"},
            ],
        },
        "checks": [
            r"up to \$5,000",
            r"up to \$150,000",
        ],
    },
    {
        "id": 4103,
        "name": "AWS Activate",
        "type": "infra",
        "amount": "Up to $100K",
        "amountText": "Up to 100K USD",
        "amountNote": "$1K founders path, more via providers",
        "desc": "AWS offers a low-friction founders path and a bigger provider-backed path for cloud runway.",
        "tags": ["Official source", "AWS credits", "Bedrock eligible"],
        "eligibility": "easy",
        "eligLabel": "Apply now",
        "fit": "Immediate",
        "signal": {"speed": "Fast", "leverage": "High", "friction": "Low"},
        "details": {
            "benefit": "AWS Activate includes a founders path and larger provider-backed credit options that can offset infrastructure and model usage.",
            "eligibility": ["Early-stage startup", "AWS account", "Provider route for larger credit tier"],
            "docs": ["Startup details", "AWS account", "Company website or profile"],
            "how": "Start with the founders route if needed, then upgrade through an incubator or provider relationship.",
            "tip": "Strongest when treated as a runway extender rather than the center of the fundraising story.",
            "url": "https://aws.amazon.com/activate/",
            "sources": [
                {"label": "AWS Activate", "url": "https://aws.amazon.com/activate/"},
                {"label": "AWS credit eligibility", "url": "https://aws.amazon.com/activate/portfolio-signup"},
            ],
        },
        "checks": [
            r"up to \$100,000",
            r"Activate Founders",
        ],
    },
    {
        "id": 4104,
        "name": "NVIDIA Inception",
        "type": "infra",
        "amount": "Free",
        "amountText": "Free program",
        "amountNote": "AI tools, offers, investor access",
        "desc": "NVIDIA's startup program is relevant if ConnectorsATS grows into AI-led matching or ranking.",
        "tags": ["Official source", "AI program", "No cohorts"],
        "eligibility": "easy",
        "eligLabel": "Apply now",
        "fit": "Immediate",
        "signal": {"speed": "Fast", "leverage": "Medium", "friction": "Low"},
        "details": {
            "benefit": "NVIDIA describes Inception as a free startup program with training, tools, partner offers, and investor access.",
            "eligibility": ["AI startup at any stage", "No application fee", "No listed cohort deadline"],
            "docs": ["Startup profile", "Product details", "Business description"],
            "how": "Apply directly through the NVIDIA Inception page if AI is part of the roadmap.",
            "tip": "Position ConnectorsATS around AI-assisted matching only if that is truly part of the product core.",
            "url": "https://www.nvidia.com/en-us/startups/",
            "sources": [
                {"label": "NVIDIA Inception", "url": "https://www.nvidia.com/en-us/startups/"},
                {"label": "NVIDIA FAQ", "url": "https://www.nvidia.com/en-us/startups/faq/"},
            ],
        },
        "checks": [
            r"free program",
            r"preferred pricing",
            r"investors",
        ],
    },
    {
        "id": 4105,
        "name": "GitHub for Startups",
        "type": "infra",
        "amount": "$10K",
        "amountText": "10K credits",
        "amountNote": "Enterprise platform credits",
        "desc": "Useful when the engineering workflow matures and enterprise tooling starts to matter.",
        "tags": ["Official source", "Developer stack", "Partner-affiliated"],
        "eligibility": "medium",
        "eligLabel": "Needs partner or funding path",
        "fit": "Near-term",
        "signal": {"speed": "Medium", "leverage": "Medium", "friction": "Partner-linked"},
        "details": {
            "benefit": "GitHub promotes startup credits and discounted enterprise tooling for eligible startups.",
            "eligibility": ["Startup with outside funding or approved partner route", "New to relevant GitHub plans", "Company email"],
            "docs": ["Company email", "Startup details", "Funding or partner context"],
            "how": "Apply once the engineering workflow justifies enterprise tooling or an approved partner path exists.",
            "tip": "More useful once release workflow and security tooling start becoming real needs.",
            "url": "https://github.com/enterprise/startups",
            "sources": [{"label": "GitHub for Startups", "url": "https://github.com/enterprise/startups"}],
        },
        "checks": [
            r"\$10,000",
            r"up to 20 seats",
        ],
    },
]


class FeedState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.generated_at = 0.0
        self.payload: dict[str, Any] | None = None


STATE = FeedState()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_html(url: str, timeout: int = 15) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        },
    )
    with urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_title(html: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if not match:
      return ""
    title = unescape(match.group(1))
    return re.sub(r"\s+", " ", title).strip()


def build_snippet(text: str, checks: list[str]) -> str:
    for pattern in checks:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(match.start() - 80, 0)
            end = min(match.end() + 120, len(text))
            snippet = text[start:end].strip(" .")
            return re.sub(r"\s+", " ", snippet)
    return ""


def build_dynamic_feed() -> dict[str, Any]:
    opportunities: list[dict[str, Any]] = []
    for seed in SCRAPE_TARGETS:
        page_title = ""
        snippet = ""
        verified = False
        error_message = ""
        try:
            html = read_html(seed["details"]["url"])
            text = html_to_text(html)
            page_title = extract_title(html)
            snippet = build_snippet(text, seed.get("checks", []))
            verified = True
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            error_message = str(error)

        opp = json.loads(json.dumps(seed))
        generated_tags = list(opp["tags"])
        generated_tags.append(f"Checked {datetime.now().strftime('%d %b %Y')}")
        if verified:
            generated_tags.append("Live verified")
        else:
            generated_tags.append("Using fallback metadata")
        opp["tags"] = generated_tags

        tip = opp["details"]["tip"]
        if page_title:
            tip = f"{tip} Last verified against: {page_title}."
        if snippet:
            tip = f"{tip} Evidence: {snippet}"
        elif error_message:
            tip = f"{tip} Live verification unavailable during the latest fetch."
        opp["details"]["tip"] = tip
        opp["details"]["sources"] = list(opp["details"]["sources"]) + [
            {"label": "Live feed generator", "url": "http://localhost:8765/connectorsATS_live_feed.json"}
        ]
        opportunities.append(opp)

    payload = {
        "generatedBy": "connectorsats_live_server.py",
        "generatedAt": now_iso(),
        "opportunities": opportunities,
    }
    CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def get_feed(force: bool = False) -> dict[str, Any]:
    with STATE.lock:
        is_stale = (time.time() - STATE.generated_at) > CACHE_TTL_SECONDS
        if force or STATE.payload is None or is_stale:
            try:
                STATE.payload = build_dynamic_feed()
                STATE.generated_at = time.time()
            except Exception:
                if CACHE_FILE.exists():
                    STATE.payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                    STATE.generated_at = time.time()
                elif STATE.payload is None:
                    STATE.payload = {
                        "generatedBy": "connectorsats_live_server.py",
                        "generatedAt": now_iso(),
                        "opportunities": [],
                    }
        return STATE.payload


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html", "/connectorsATS_opportunities_dashboard.html"}:
            self.serve_html()
            return

        if self.path.startswith("/connectorsATS_live_feed.json"):
            self.serve_feed()
            return

        super().do_GET()

    def serve_html(self) -> None:
        content = HTML_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_feed(self) -> None:
        payload = get_feed(force=True)
        content = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    get_feed(force=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), DashboardHandler)
    print(f"ConnectorsATS dashboard running at http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
