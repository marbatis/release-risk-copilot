"""Sample release bundle loader for deterministic MVP demos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.schemas.models import ReleaseBundle

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_bundles"


class SampleDataRepository:
    """Load release bundle fixtures from local JSON files."""

    def __init__(self, sample_dir: Optional[Path] = None) -> None:
        self.sample_dir = (sample_dir or DEFAULT_SAMPLE_DIR).resolve()

    def list_samples(self) -> list[str]:
        """Return available sample bundle names without file extension."""

        return sorted(path.stem for path in self.sample_dir.glob("*.json"))

    def load_sample(self, sample_name: str) -> ReleaseBundle:
        """Load one release bundle fixture by name."""

        safe_name = Path(sample_name).name
        if not safe_name.endswith(".json"):
            safe_name = f"{safe_name}.json"

        sample_path = (self.sample_dir / safe_name).resolve()
        if not sample_path.exists():
            raise FileNotFoundError(f"Sample bundle not found: {sample_name}")

        if sample_path.parent != self.sample_dir:
            raise ValueError("Invalid sample path")

        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        return ReleaseBundle.model_validate(payload)
