"""Shared "is this evidence real?" check used both to validate a fresh
extraction (before spending a GENERATE call on it) and to validate the
final generated report (before trusting it). Deliberately a single,
reusable, pure function — the same rule ("a quote must appear verbatim in
the source text") applies at both points in the pipeline.
"""


def find_ungrounded_quotes(quotes: list[str], source_text: str) -> list[str]:
    """Return the subset of `quotes` that do NOT appear verbatim in
    `source_text`. An empty result means every quote is grounded.
    """
    return [quote for quote in quotes if quote not in source_text]
