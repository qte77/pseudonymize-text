"""Optional spaCy NER adapter (issue #12 / ARCHITECTURE.md).

Off by default. Installation:
    uv sync --extra ner
    pip install <pinned wheel URL for xx_ent_wiki_sm==3.7.0> --require-hashes

See docs/ner-install.md for the pinned model URL + hash. Loading
``xx_ent_wiki_sm`` via ``spacy.load`` after ``spacy download`` works
locally but is forbidden in CI / production because it pulls whatever
the spaCy catalogue currently points at (silent supply-chain drift).
"""

from collections.abc import Iterator

from ..replacer import Span

_LABEL_TO_TYPE: dict[str, str] = {
    "PERSON": "name",
    "ORG": "org",
    "GPE": "loc",
    "LOC": "loc",
}


def detect_ner(
    text: str,
    *,
    model_name: str = "xx_ent_wiki_sm",
    stoplist: frozenset[str] = frozenset(),
) -> Iterator[Span]:
    """Yield ``Span`` for each named entity spaCy recognises in ``text``.

    Lazy-imports ``spacy`` so the core package stays dep-light. Raises
    ``ImportError`` with an actionable install hint if the ``[ner]``
    extra is not installed.

    Label mapping (spaCy → our type): ``PERSON``→``name``, ``ORG``→``org``,
    ``GPE``/``LOC``→``loc``. Other labels are dropped.

    ``stoplist`` entries are compared case-insensitively against each
    entity's surface text and exclude matches.
    """
    try:
        import spacy
    except ImportError as exc:
        raise ImportError(
            "spaCy is not installed; install the [ner] extra: "
            "`uv sync --extra ner` (see docs/ner-install.md)"
        ) from exc

    nlp = spacy.load(model_name)
    stop_lc = {s.lower() for s in stoplist}
    for ent in nlp(text).ents:
        type_ = _LABEL_TO_TYPE.get(ent.label_)
        if type_ is None:
            continue
        if ent.text.lower() in stop_lc:
            continue
        yield Span(
            start=ent.start_char,
            end=ent.end_char,
            text=ent.text,
            type=type_,
            detector=f"ner:{ent.label_}",
        )
