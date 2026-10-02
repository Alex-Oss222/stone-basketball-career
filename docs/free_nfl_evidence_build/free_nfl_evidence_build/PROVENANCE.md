# Provenance

This package contains code only. It does not bundle NFL statistics.

At run time it downloads public release assets from `nflverse/nflverse-data` and stores a local SHA-256 manifest. The intended source families are play-by-play, player stats, weekly rosters, injuries, depth charts, PFR snap counts, and the nflverse player crosswalk.

The project deliberately excludes paid PFF/SIS/Football Outsiders datasets and does not scrape or transcribe paid charting.
