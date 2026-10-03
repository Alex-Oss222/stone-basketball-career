"""Read-only, detailed career screens served by the existing engine deployment.

The normal report builder is the sole source for the interactive screens. No
example fixture, game draw, player decision or career-clock mutation runs here.
"""
from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit


def _safe_href(value):
    value = value.strip()
    scheme = urlsplit(value).scheme.lower()
    return value if scheme in ("", "http", "https", "mailto") and not value.startswith("//") else "#"


def _inline(value):
    """A small escaped Markdown subset for public source records, not HTML input."""
    placeholders = []

    def keep(markup):
        placeholders.append(markup)
        return f"\x00{len(placeholders)-1}\x00"

    def link(match):
        label, target = match.group(1), match.group(2)
        return keep(f'<a href="{escape(_safe_href(target), quote=True)}">{escape(label)}</a>')

    value = re.sub(r"!\[([^\]]*)\]\(([^\s)]+)\)", lambda m: keep(
        f'<img src="{escape(_safe_href(m[2]), quote=True)}" alt="{escape(m[1], quote=True)}">'), value)
    value = re.sub(r"\[([^\]]+)\]\(([^\s)]+)\)", link, value)
    value = escape(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    # Restore outer links before their inner image tokens.
    for index in range(len(placeholders) - 1, -1, -1):
        value = value.replace(f"\x00{index}\x00", placeholders[index])
    return value


def source_page(text, title, *, is_json=False):
    """Render full source detail safely; tables scroll rather than losing columns."""
    if is_json:
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except ValueError:
            pass
        body = "<pre>" + escape(text) + "</pre>"
    else:
        parts, table, code, code_lines = [], False, False, []
        for line in text.splitlines():
            if line.startswith("```"):
                if code:
                    parts.append("<pre>" + escape("\n".join(code_lines)) + "</pre>")
                    code_lines = []
                code = not code
                continue
            if code:
                code_lines.append(line)
                continue
            is_table = line.startswith("|") and line.endswith("|")
            if table and not is_table:
                parts.append("</tbody></table></div>")
                table = False
            if is_table:
                cells = line.strip("|").split("|")
                if all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in cells):
                    continue
                if not table:
                    parts.append('<div class="table-scroll"><table><tbody>')
                    table = True
                parts.append("<tr>" + "".join("<td>" + _inline(c.strip()) + "</td>" for c in cells) + "</tr>")
            elif line.startswith("#"):
                match = re.match(r"^(#{1,6})\s+(.*)", line)
                if match:
                    level, content = len(match[1]), match[2]
                    anchor = re.sub(r"[^\w -]", "", content.lower()).replace(" ", "-")
                    parts.append(f'<h{level} id="{escape(anchor, quote=True)}">{_inline(content)}</h{level}>')
                else:
                    parts.append("<p>" + _inline(line) + "</p>")
            elif line.startswith("<!--") or line.startswith("<details") or line == "</details>" or line.startswith("<summary>"):
                continue
            elif line:
                parts.append("<p>" + _inline(line) + "</p>")
        if code:
            parts.append("<pre>" + escape("\n".join(code_lines)) + "</pre>")
        if table:
            parts.append("</tbody></table></div>")
        body = "\n".join(parts)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | Career record</title>
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0c0d11;color:#ececf0;font:15px/1.65 system-ui,sans-serif}}main{{max-width:1280px;margin:auto;padding:28px 24px 70px;overflow-wrap:anywhere}}nav{{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #443039;padding-bottom:18px;margin-bottom:26px}}a{{color:#ec9aac}}h1{{font-size:32px}}h2{{margin-top:35px;border-bottom:1px solid #32262b;padding-bottom:9px}}h3{{margin-top:27px}}img{{max-width:100%;height:auto}}pre{{overflow:auto;white-space:pre-wrap;background:#151820;border:1px solid #30333d;padding:22px;border-radius:8px}}code{{color:#edc591}}.table-scroll{{overflow:auto;margin:18px 0}}table{{border-collapse:collapse;min-width:100%;font-size:13px}}td{{border:1px solid #353139;padding:11px;white-space:nowrap}}tr:first-child{{background:#501d2c;font-weight:700}}a:focus-visible{{outline:3px solid #f2c56a;outline-offset:4px}}</style></head>
<body><main><nav><a href="/career">Career desk</a><a href="/cards">Shooting, Contract and Awards</a><a href="/contracts">Player contracts</a><a href="/games">Engine results</a></nav>{body}</main></body></html>'''


class CareerSite:
    """An in-memory report snapshot plus narrowly scoped public record serving."""

    def __init__(self, root, revision=None):
        from .player_reports import build_reports
        self.root = Path(root).resolve()
        self.pages = {}
        players = sorted(p for p in (self.root / "career").iterdir() if p.is_dir() and (p / "professional_identity.json").is_file())
        if not players:
            raise ValueError("no canonical player identity is available for the career desk")
        self.player = players[0]
        for player in players:
            for path, content in build_reports(self.root, player).items():
                self.pages["/" + path.relative_to(self.root).as_posix()] = content
        self.library_sources = set()
        for page, content in self.pages.items():
            for groups in re.findall(r'''\]\(([^)\s]+)\)|href=["']([^"']+)["']''', content):
                href = unescape(next(value for value in groups if value))
                if urlsplit(href).scheme or href.startswith("//"):
                    continue
                target = urlsplit(urljoin(page, href)).path
                if target.startswith("/library/") and not target.startswith("/library/careers/"):
                    self.library_sources.add(target)
        base = "/" + self.player.relative_to(self.root).as_posix()
        self.home = base + "/Milestones/index.html"
        self.cards = base + "/Stats_and_Awards/player_cards.html"
        self.contracts = base + "/Contracts/index.html"
        if self.home not in self.pages or self.cards not in self.pages:
            raise ValueError("live milestone and player card screens were not generated")
        states = [json.loads(p.read_text()) for p in self.player.glob("*/current_state.json")]
        current = max(states, key=lambda s: s["current_date"])
        self.status = {"screen_version": 1, "mode": "canonical", "detail": "full", "revision": revision,
                       "as_of": current["current_date"], "season": current["season"],
                       "milestones": self.home, "player_cards": self.cards,
                       "contracts": self.contracts,
                       "generated_pages": len(self.pages)}

    def resource(self, request_path):
        """Return (body, MIME), or None. Never serve arbitrary files or secrets."""
        path = unquote(request_path)
        bits = path.split("/")
        if "\x00" in path or "\\" in path or any(p in (".", "..") or p.startswith(".") for p in bits if p):
            return None
        if len(bits) < 3 or bits[1] not in {"career", "docs", "library"}:
            return None
        # Engine talent trajectories and future world rosters never become a
        # browseable library through the live player site. Serve only evidence
        # explicitly linked by the dated canonical views.
        if bits[1] == "library" and path not in self.library_sources:
            return None
        target = (self.root / path.lstrip("/")).resolve()
        allowed_root = self.root / bits[1]
        if not target.is_relative_to(allowed_root):
            return None
        if target.is_dir():
            path += "/README.md" if not path.endswith("/") else "README.md"
            target /= "README.md"
        suffix = target.suffix.lower()
        if suffix not in {".html", ".md", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".js", ".css"}:
            return None
        # Only generated canonical HTML runs as an app. Documentation examples
        # remain files in the repo, never an accidental production player view.
        if suffix in {".html", ".js", ".css"} and path not in self.pages:
            return None
        content = self.pages.get(path)
        if content is None:
            if not target.is_file() or target.stat().st_size > 12 * 1024 * 1024:
                return None
            if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                return target.read_bytes(), {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[suffix]
            content = target.read_text(encoding="utf-8")
        if suffix == ".md":
            return source_page(content, target.stem), "text/html"
        return content, {".html": "text/html", ".json": "application/json", ".svg": "image/svg+xml",
                         ".js": "text/javascript", ".css": "text/css"}[suffix]
