"""Detailed, read-only contract pages and a directory for every tracked player."""
from __future__ import annotations

from datetime import date
from html import escape
import json
import os
from pathlib import Path
import re

from .player_contracts import build_contract_catalog, contract_payload

GENERATED = "<!-- Generated from dated contract records by scripts/update_player_reports.py. -->\n"


def relative(page, target):
    return Path(os.path.relpath(target, page.parent)).as_posix()


def encoded(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def shared_template(template, folder):
    """Share presentation assets across hundreds of independent player URLs."""
    outputs = {}
    styles = re.findall(r"<style>(.*?)</style>", template, re.S)
    scripts = re.findall(r"<script>(.*?)</script>", template, re.S)
    if not styles or not scripts or template.count("__PLAYER_CARD_DATA__") != 1:
        raise ValueError("contract pages require the shared player-card template")
    outputs[folder / "assets/player_cards.css"] = "\n".join(styles) + "\n"
    outputs[folder / "assets/player_cards.js"] = "\n".join(scripts) + "\n"
    template = re.sub(r"<style>.*?</style>", "", template, flags=re.S)
    template = template.replace("</head>", '<link rel="stylesheet" href="../assets/player_cards.css"></head>')
    template = re.sub(r"<script>.*?</script>", "", template, flags=re.S)
    template = template.replace("</body>", '<script src="../assets/player_cards.js"></script></body>')
    return template, outputs


def _text(value):
    if value is None:
        return "Not recorded"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        return str(value.get("text", value.get("label", value.get("value", "Not recorded"))))
    return str(value)


def _md(value):
    if isinstance(value, dict) and value.get("href"):
        label = str(value.get("label", value.get("text", "Source"))).replace("|", "&#124;").replace("\n", " ")
        return f'[{label}]({value["href"]})'
    if isinstance(value, dict) and value.get("label") and "value" in value:
        return _md(value["label"]) + ": " + _md(value["value"])
    return _text(value).replace("|", "&#124;").replace("\n", " ")


def table(headers, rows):
    return "| " + " | ".join(map(_md, headers)) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "".join(
        "| " + " | ".join(map(_md, row)) + " |\n" for row in rows) + "\n"


def section_markdown(section):
    text = "### " + _text(section.get("title", "Contract detail")) + "\n\n"
    for field in ("body", "description", "summary", "notice", "note", "empty"):
        if section.get(field):
            values = section[field] if isinstance(section[field], list) else [section[field]]
            text += "\n\n".join(_text(value) for value in values) + "\n\n"
    if section.get("fields"):
        fields = section["fields"]
        text += table(["Term", "Recorded detail"], [[f.get("label"), f.get("value")] if isinstance(f, dict) else f for f in fields])
    headers = section.get("columns") or section.get("headers")
    if headers:
        labels = [h.get("label", h.get("key")) if isinstance(h, dict) else h for h in headers]
        rows = section.get("rows", [])
        if rows and isinstance(rows[0], dict):
            rows = [[row.get(h.get("key", h.get("label"))) if isinstance(h, dict) else row.get(h) for h in headers] for row in rows]
        text += table(labels, rows)
    for item in section.get("items", []):
        text += "- " + _md(item) + "\n"
    if section.get("items"):
        text += "\n"
    return text


def source_markdown(sources):
    if not sources:
        return "No additional signed document is recorded.\n\n"
    return "\n".join(f'- [{_md(s.get("label", "Source record"))}]({s["href"]})' if s.get("href") else "- " + _md(s.get("label", s))
                     for s in sources) + "\n\n"


def contract_markdown(payload, name, *, interactive):
    text = GENERATED + f"\n# Contract | {name}\n\n"
    text += f'Known through: {payload["as_of"]}. [Open interactive contract]({interactive}#contract) · [Contract history]({interactive}#contract-history)\n\n'
    text += _text(payload.get("summary", "Contract evidence at the career checkpoint.")) + "\n\n"
    text += "## Current contract\n\n"
    current = payload.get("current")
    if current:
        text += record_markdown(current)
    else:
        text += "No verified current signed agreement is available in the dated record. The control and evidence sections below explain the recorded status.\n\n"
    for section in payload.get("sections", []):
        text += section_markdown(section)
    text += "## Contract history\n\n"
    history = payload.get("history", [])
    if not history:
        text += "No executed agreement is recorded in the available contract history.\n\n"
    else:
        text += "The register preserves distinct agreements. An assignment by trade is part of the same agreement.\n\n"
        for contract in history:
            text += record_markdown(contract)
    text += "## Source records\n\n" + source_markdown(payload.get("sources", []))
    return text


def record_markdown(contract):
    text = "### " + _text(contract.get("title", "Recorded agreement")) + "\n\n"
    text += _text(contract.get("summary", "")) + "\n\n"
    metrics = contract.get("metrics", [])
    if metrics:
        text += table(["Contract term", "Recorded value", "Basis"], [[m.get("label"), m.get("value"), m.get("detail", "")] for m in metrics])
    for section in contract.get("sections", []):
        text += section_markdown(section)
    return text + "#### Agreement evidence\n\n" + source_markdown(contract.get("sources", []))


def profile_identity(profile, registry, clock):
    entry = registry.get(profile["id"], profile.get("identity", {}))
    born = entry.get("birth_date")
    age = None
    if born:
        birthday, cutoff = date.fromisoformat(born), date.fromisoformat(clock)
        age = cutoff.year - birthday.year - ((cutoff.month, cutoff.day) < (birthday.month, birthday.day))
    name = profile["name"]
    return dict(name=name, team=profile.get("team") or entry.get("team_name") or "Team not recorded",
                jersey=None, position=entry.get("position") or "Position not recorded", age=age,
                height="Not recorded", weight="Not recorded", shoots="Not recorded",
                entry="Dated contract record", photo_url=None,
                initials="".join(word[0] for word in name.split())[:2], status=profile.get("status", "Not recorded"), cutoff=clock)


DIRECTORY_CSS = """:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b0d12;color:#f0f0f2;font:14px/1.6 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:30px 24px 70px}a{color:#ec9cac}nav{display:flex;flex-wrap:wrap;gap:24px;margin-bottom:36px}h1{font-size:clamp(32px,5vw,54px);line-height:1.1;margin:0 0 16px;letter-spacing:-1px}h2{margin-top:32px;font-size:18px}.eyebrow{color:#ed758e;text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:2px}.lead{max-width:820px;color:#b8bbc5}.facts{display:flex;gap:14px;flex-wrap:wrap;margin:25px 0}.fact{border:1px solid #48303a;border-radius:9px;background:#20151c;padding:16px 25px}.fact strong{display:block;font-size:26px}.fact span{color:#d5bac3;font-size:11px}.controls{display:grid;grid-template-columns:2fr 1fr 1fr;gap:16px;margin:24px 0}label{font-size:12px;color:#c3c3cb}input,select{display:block;width:100%;margin-top:7px;min-height:44px;background:#171a23;color:white;border:1px solid #45434e;border-radius:6px;padding:9px 12px;font:inherit}.table-scroll{overflow:auto;max-width:100%;border:1px solid #39303a;border-radius:9px}table{border-collapse:collapse;width:100%;min-width:870px}th,td{padding:15px;text-align:left;border-bottom:1px solid #302c34}th{background:#421b29;color:#f3d6dd;font-size:11px;text-transform:uppercase;letter-spacing:.5px}td{font-size:12px;vertical-align:top}td:first-child a{font-weight:750;color:#f5eef0;font-size:14px}small{display:block;color:#989da9;font-size:11px;max-width:280px}tr:hover{background:#18171f}.result{color:#a5a8b2;font-size:12px;margin:12px 0}a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #e8bb63;outline-offset:4px}footer{margin-top:35px;font-size:12px;color:#a9a9b4}#empty{padding:24px;background:#20151c;border:1px solid #48303a}@media(max-width:650px){main{padding:24px 16px}.controls{grid-template-columns:1fr}.facts{gap:8px}.fact{padding:12px 16px}.fact strong{font-size:22px}}[hidden]{display:none!important}@media print{.controls{display:none}body{background:white;color:black}a,td:first-child a{color:black}main{max-width:none;padding:0}.table-scroll{overflow:visible}table{min-width:0}th{background:#eee;color:black}small{color:#444}}"""


def build_contract_pages(root, player, clock, *, catalog=None):
    catalog = catalog or build_contract_catalog(root, player, clock)
    folder = player / "Contracts"
    template = (Path(__file__).parent / "assets/player_cards.html").read_text(encoding="utf-8")
    shared, outputs = shared_template(template, folder)
    registry_file = player / "Stats_and_Awards/League/player_registry.json"
    registry = {p["registry_id"]: p for p in json.loads(registry_file.read_text())["players"]} if registry_file.is_file() else {}
    directory, summaries = [], []
    for profile in catalog["players"]:
        pid = profile["id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", pid):
            raise ValueError("invalid contract player identifier")
        page = folder / "players" / f"{pid}.html"
        contract = contract_payload(profile, page=page, root=root)
        identity = profile_identity(profile, registry, clock)
        if pid == catalog["default_player_id"] and (player / "professional_identity.json").is_file():
            from .player_cards import identity_payload
            identity = identity_payload(json.loads((player / "professional_identity.json").read_text()), clock)
        payload = dict(schema_version=1, mode="live", identity=identity, clock=clock,
                       notice=f"Contract evidence available through {clock}. Unrecorded terms remain unavailable.",
                       enabled_tabs=["contract"], defaultTab="contract", default_tab="contract", periods=[],
                       awards=dict(default_scenario=None, scenarios=[]), contracts=contract,
                       links=dict(stats="../index.html", contracts="../index.html", contract=f"{pid}.md",
                                  definitions=relative(page, root / "docs/player_contract_pages.md"),
                                  milestones=relative(page, player / "Milestones/index.html")))
        outputs[page] = shared.replace("__PLAYER_CARD_DATA__", encoded(payload))
        outputs[page.with_suffix(".md")] = contract_markdown(contract, profile["name"], interactive=page.name)
        current = contract.get("current")
        current_title = current.get("title", "Recorded agreement") if current else "No verified current agreement"
        status = _text(contract.get("status", profile.get("status"))).replace("_", " ")
        team = identity["team"]
        signed = current.get("signed_on") if current else None
        history_count = len(contract.get("history", []))
        directory.append(dict(id=pid, name=profile["name"], team=team, status=status,
                              current=current_title, signed=signed, history=history_count,
                              summary=_text(contract.get("summary")), href=f"players/{pid}.html#contract"))
        summaries.append(dict(player_id=pid, name=profile["name"], team=team, status=status,
                              current_contract_id=current.get("id") if current else None,
                              recorded_agreements=history_count, href=f"players/{pid}.html#contract"))
    directory.sort(key=lambda p: p["name"].casefold())
    outputs[folder / "catalog.json"] = json.dumps(dict(schema_version=1, as_of=clock, players=summaries), indent=2, ensure_ascii=False) + "\n"
    outputs[folder / "index.html"] = directory_html(directory, clock)
    outputs[folder / "README.md"] = GENERATED + f"\n# Player contracts\n\nKnown through {clock}. [Search the contract directory](index.html)\n\n" + \
        "Every tracked player has a current-contract view and complete available agreement history. Unknown terms stay explicit. Signed value, salary, guarantees and cap charges remain separate.\n\n" + \
        table(["Player", "Recorded team", "Status", "Current agreement", "History entries"], [
            [f'[{p["name"]}](players/{p["id"]}.md)', p["team"], p["status"], p["current"], p["history"]] for p in directory])
    return outputs


def directory_html(rows, clock):
    teams = sorted({p["team"] for p in rows})
    statuses = sorted({p["status"] for p in rows})
    options = lambda values: "".join(f'<option value="{escape(v, quote=True)}">{escape(v)}</option>' for v in values)
    body = "".join(f'<tr data-name="{escape(p["name"].casefold(), quote=True)}" data-team="{escape(p["team"], quote=True)}" data-status="{escape(p["status"], quote=True)}">'
                   f'<td><a href="{p["href"]}">{escape(p["name"])}</a><small>{escape(p["id"])}</small></td>'
                   f'<td>{escape(p["team"])}</td><td>{escape(p["status"])}</td>'
                   f'<td>{escape(p["current"])}<small>{escape(p["summary"])}</small></td>'
                   f'<td>{escape(_text(p["signed"]))}</td><td><a href="players/{p["id"]}.html#contract-history">{p["history"]} recorded</a></td></tr>' for p in rows)
    known = sum(p["current"] != "No verified current agreement" for p in rows)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Player contracts | Stone Basketball Career</title><style>{DIRECTORY_CSS}</style></head><body><main>
<nav><a href="../Milestones/index.html">Career desk</a><a href="../Stats_and_Awards/player_cards.html#contract">Your contract</a><a href="../Stats_and_Awards/player_cards.html">Shooting, Contract and Awards</a><a href="README.md">Full directory record</a></nav>
<p class="eyebrow">NBA contract register · {clock}</p><h1>Every player. Every recorded term.</h1>
<p class="lead">Open a player to inspect the current agreement, season-by-season salary, guarantees, options, rights, clauses, evidence and contract history. Each page follows the career's dated records and states where terms are incomplete.</p>
<div class="facts"><div class="fact"><strong>{len(rows)}</strong><span>TRACKED PLAYERS</span></div><div class="fact"><strong>{known}</strong><span>RECORDED CURRENT AGREEMENTS</span></div><div class="fact"><strong>{clock}</strong><span>KNOWLEDGE DATE</span></div></div>
<div class="controls"><label>Find a player<input id="search" type="search" placeholder="Search player name" autocomplete="off"></label><label>Recorded team<select id="team"><option value="">All teams</option>{options(teams)}</select></label><label>Contract status<select id="status"><option value="">All statuses</option>{options(statuses)}</select></label></div>
<p class="result" id="count" role="status" aria-live="polite">{len(rows)} players</p><div class="table-scroll" tabindex="0" role="region" aria-label="Player contract directory"><table><thead><tr><th scope="col">Player</th><th scope="col">Team / rights</th><th scope="col">Status</th><th scope="col">Current agreement / coverage</th><th scope="col">Signed on</th><th scope="col">Contract history</th></tr></thead><tbody>{body}</tbody></table></div><p id="empty" hidden>No players match these filters. Change the name, team or status to see more records.</p>
<footer>Signed contract value is not actual cash earned. Draft holds, free-agent holds, pending offers and conditional options are labeled separately. Historical reconstruction is identified on each page. <a href="../../../docs/player_contract_pages.md">Source and update guide</a> · <a href="catalog.json">Directory data</a></footer></main>
<script>const rows=[...document.querySelectorAll('tbody tr')];const q=document.getElementById('search'),team=document.getElementById('team'),status=document.getElementById('status');const normalize=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();function filter(){{let n=0;for(const row of rows){{const match=normalize(row.dataset.name).includes(normalize(q.value.trim()))&&(!team.value||row.dataset.team===team.value)&&(!status.value||row.dataset.status===status.value);row.hidden=!match;n+=Number(match);}}document.getElementById('count').textContent=n+' of '+rows.length+' players';document.getElementById('empty').hidden=n!==0;}}q.addEventListener('input',filter);team.addEventListener('change',filter);status.addEventListener('change',filter);</script></body></html>'''
