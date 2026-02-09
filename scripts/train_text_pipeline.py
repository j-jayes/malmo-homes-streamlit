"""Train the text-to-price pipeline and print results.

Usage::

    python scripts/train_text_pipeline.py
    python scripts/train_text_pipeline.py --alpha 50 --log-level DEBUG
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.text_pipeline import main

if __name__ == "__main__":
    main()
