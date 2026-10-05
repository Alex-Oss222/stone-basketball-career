"""Decision requests: chance-based career decisions drawn by the engine like games.

A decision request (`*.decision.json`, in the phase folder it belongs to) names
the question, the date and each option's probability. The Railway engine
journals it and draws one option, so the outcome cannot be chosen or
re-rolled; an edited request is refused once drawn.

    {
      "event_id": "2003-06-30-carter-player-option",
      "date": "2003-06-30",
      "question": "Does Anthony Carter exercise his 2003-04 player option?",
      "decider": "Anthony Carter (simulated player)",
      "options": {"exercise": 0.645, "decline": 0.355},
      "basis": "why these probabilities"
    }
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"event_id", "date", "question", "decider", "options", "basis"}
ENTROPY_DOMAIN = b"stone-basketball-career/decision-entropy/v1\0"
PROCEDURE = "decision-v1"
# Roadmap 18b: from this date every decision has a semantic key (its date and the hash of its question, normalised),
# unique across the journal, so the same question cannot be drawn again under a new event id.
HARDEN_FROM = "2004-07-01"


def semantic_key(data):
    """kind / subject / date in one key: the decision date and the normalised question it answers."""
    question = " ".join(str(data.get("question", "")).lower().split())
    return f"{data.get('date')}:{hashlib.sha256(question.encode()).hexdigest()[:24]}"


def hardened(data):
    return isinstance(data.get("date"), str) and data["date"] >= HARDEN_FROM


def key_errors(root=ROOT):
    """Committed decisions dated from HARDEN_FROM whose semantic key repeats under another event id."""
    seen, errors = {}, []
    for path in find_decisions(root):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not hardened(data):
            continue
        key = semantic_key(data)
        if key in seen and seen[key] != data["event_id"]:
            errors.append(f"{path.relative_to(root)}: the same question on {data['date']} was already asked as {seen[key]}")
        seen.setdefault(key, data["event_id"])
    return errors


def find_decisions(root=ROOT):
    return sorted((Path(root) / "career").rglob("*.decision.json"))


def load_decision(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = decision_errors(data)
    if errors:
        raise ValueError("; ".join(errors))
    return data


def decision_errors(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        return [f"decision fields must be exactly {sorted(FIELDS)}"]
    errors = []
    options = data["options"]
    if not isinstance(options, dict) or len(options) < 2:
        errors.append("a decision needs at least two options")
    elif any(not isinstance(p, (int, float)) or isinstance(p, bool) or not 0 < p < 1 for p in options.values()):
        errors.append("each option probability must be strictly between 0 and 1")
    elif abs(sum(options.values()) - 1) > 1e-9:
        errors.append("option probabilities must sum to 1")
    if not all(isinstance(data[k], str) and data[k].strip() for k in ("event_id", "date", "question", "decider", "basis")):
        errors.append("event_id, date, question, decider and basis must be nonempty text")
    return errors


def packet(data):
    return {"procedure": PROCEDURE, **{k: data[k] for k in sorted(FIELDS)}}


def draw(data, journal):
    """Journal the decision, then pick an option from the opaque reference."""
    ref = journal.close_event(packet(data))  # durable closure precedes the draw
    point = int.from_bytes(hashlib.sha256(ENTROPY_DOMAIN + bytes.fromhex(ref)).digest()[:8], "big") / 2 ** 64
    running = 0.0
    for name, probability in sorted(data["options"].items()):
        running += probability
        if point < running:
            return name
    return sorted(data["options"])[-1]
