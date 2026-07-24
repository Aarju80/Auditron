from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return _FIXTURES_DIR


@pytest.fixture
def load_fixture(fixtures_dir: Path):
    def _load(name: str) -> str:
        path = fixtures_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"Fixture not found: {path}\n"
                f"Available fixtures: {sorted(p.name for p in fixtures_dir.iterdir())}"
            )
        return path.read_text(encoding="utf-8")

    return _load
