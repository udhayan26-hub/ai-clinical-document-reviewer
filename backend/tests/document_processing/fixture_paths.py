from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


def load_pdf_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()
