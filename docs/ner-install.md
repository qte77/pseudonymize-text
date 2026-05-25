# NER installation (optional)

The NER detector is gated behind the `[ner]` extra. Operators who need it must install both spaCy and a pinned, hash-verified model.

## 1. Install spaCy

```bash
uv sync --extra ner
```

This installs `spacy>=3.7` from `pyproject.toml`.

## 2. Install the pinned model

Do **not** use `python -m spacy download xx_ent_wiki_sm`. The `spacy download` command resolves the model URL from the spaCy catalogue at install time, which is a silent supply-chain shift if the catalogue is updated. Use the pinned wheel URL and verify its hash:

```bash
pip install \
  'https://github.com/explosion/spacy-models/releases/download/xx_ent_wiki_sm-3.7.0/xx_ent_wiki_sm-3.7.0-py3-none-any.whl' \
  --require-hashes
```

The wheel's SHA-256 must be recorded in your environment's lockfile or in a `requirements-ner.txt`:

```text
# requirements-ner.txt (template — fill in the real hash before use)
https://github.com/explosion/spacy-models/releases/download/xx_ent_wiki_sm-3.7.0/xx_ent_wiki_sm-3.7.0-py3-none-any.whl \
  --hash=sha256:<paste hash here>
```

To compute the hash:

```bash
curl -sL <wheel URL> | sha256sum
```

## 3. Why pinning matters

The model is part of the **operator stability matrix** in [HASHING.md §7](HASHING.md#7-operator-stability-matrix). A model swap (different version, different training corpus) can shift NER output — different spans, different labels — and therefore different tokens for the same plaintext. Re-running `apply --plan` against the original report is the recovery path; for routine runs, pin once and lock the lockfile.

## 4. CI considerations

Project CI (`.github/workflows/python.yaml`) does **not** install `[ner]` — the matrix runs against the core install only. NER tests use `pytest.importorskip("spacy")` and are skipped in CI. To exercise them, run locally after step 1+2 above.
