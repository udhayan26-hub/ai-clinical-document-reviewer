from pathlib import Path

FIXTURES_ROOT = Path(__file__).parent.parent / "fixtures"
DOCUMENTS_DIR = FIXTURES_ROOT / "documents"
IMAGES_DIR = FIXTURES_ROOT / "images"


def load_pdf_fixture(name: str) -> bytes:
    return (DOCUMENTS_DIR / name).read_bytes()


def load_image_fixture(name: str) -> bytes:
    return (IMAGES_DIR / name).read_bytes()
