### Fixed

- `lychee.toml`: `include_fragments = "anchor-only"` — lychee 0.24 replaced the boolean with a mode string, so the config failed to parse and the `links` check had been red on every run. `links.yaml` now also runs when `lychee.toml` changes.
