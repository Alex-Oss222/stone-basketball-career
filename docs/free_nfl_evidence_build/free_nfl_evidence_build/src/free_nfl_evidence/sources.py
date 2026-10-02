from __future__ import annotations

import hashlib
import json
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .guards import assert_allowed_seasons, assert_output_isolated

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
USER_AGENT = "free-nfl-evidence/0.1 (+public historical research)"


@dataclass(frozen=True)
class SourceSpec:
    dataset: str
    season: int | None
    candidates: tuple[str, ...]


def _season_candidates(tag: str, stem: str, season: int, prefer_gzip: bool = False) -> tuple[str, ...]:
    csv = f"{BASE}/{tag}/{stem}_{season}.csv"
    gz = f"{BASE}/{tag}/{stem}_{season}.csv.gz"
    return (gz, csv) if prefer_gzip else (csv, gz)


def source_specs(seasons: Iterable[int]) -> list[SourceSpec]:
    seasons = assert_allowed_seasons(seasons)
    specs: list[SourceSpec] = []
    for season in seasons:
        specs.extend(
            [
                SourceSpec("player_stats", season, _season_candidates("stats_player", "stats_player_week", season)),
                SourceSpec("weekly_rosters", season, _season_candidates("weekly_rosters", "roster_weekly", season)),
                SourceSpec("injuries", season, _season_candidates("injuries", "injuries", season)),
                SourceSpec("depth_charts", season, _season_candidates("depth_charts", "depth_charts", season)),
                SourceSpec("pbp", season, _season_candidates("pbp", "play_by_play", season, prefer_gzip=True)),
            ]
        )
        if season >= 2012:
            specs.append(SourceSpec("snap_counts", season, _season_candidates("snap_counts", "snap_counts", season)))

    specs.append(
        SourceSpec(
            "players",
            None,
            (
                f"{BASE}/players/players.csv",
                f"{BASE}/players/players.csv.gz",
            ),
        )
    )
    return specs


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, destination: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def fetch_public_data(output_root: Path, seasons: Iterable[int], overwrite: bool = False) -> list[dict]:
    """Download only public nflverse release assets into an isolated workspace."""
    output_root = output_root.expanduser().resolve()
    assert_output_isolated(output_root)
    raw = output_root / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for spec in source_specs(seasons):
        suffix = "global" if spec.season is None else str(spec.season)
        last_error: Exception | None = None
        downloaded = False
        for url in spec.candidates:
            ext = ".csv.gz" if url.endswith(".csv.gz") else ".csv"
            dest = raw / f"{spec.dataset}_{suffix}{ext}"
            if dest.exists() and not overwrite:
                manifest.append(
                    {
                        "dataset": spec.dataset,
                        "season": spec.season,
                        "url": url,
                        "path": str(dest),
                        "sha256": _sha256(dest),
                        "downloaded_at_utc": None,
                        "status": "existing",
                    }
                )
                downloaded = True
                break
            try:
                tmp = dest.with_suffix(dest.suffix + ".part")
                if tmp.exists():
                    tmp.unlink()
                _download(url, tmp)
                tmp.replace(dest)
                manifest.append(
                    {
                        "dataset": spec.dataset,
                        "season": spec.season,
                        "url": url,
                        "path": str(dest),
                        "sha256": _sha256(dest),
                        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
                        "status": "downloaded",
                    }
                )
                downloaded = True
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
        if not downloaded:
            raise RuntimeError(
                f"Could not download {spec.dataset} {suffix} from any known public URL. "
                f"Last error: {last_error}"
            )

    manifest_path = output_root / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
