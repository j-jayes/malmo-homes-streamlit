"""Train the property price prediction model.

Usage::

    python scripts/train_model.py
    python scripts/train_model.py --output-dir models --n-folds 5
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.models.train_pipeline import PropertyPriceTrainer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train property price model")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models"),
        help="Directory for saving model artifacts (default: models/)",
    )
    parser.add_argument(
        "--n-folds",
        type=int,
        default=5,
        help="Number of cross-validation folds (default: 5)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    trainer = PropertyPriceTrainer(
        project_root=Path.cwd(),
        n_folds=args.n_folds,
    )

    result = trainer.train()
    print(f"\n{'=' * 60}")
    print(f"  TRAINING COMPLETE — {result.summary()}")
    print(f"{'=' * 60}")
    print(f"\nFeature importances:")
    for name, imp in sorted(
        result.feature_importances.items(), key=lambda x: -x[1]
    ):
        bar = "█" * int(imp / max(result.feature_importances.values()) * 30)
        print(f"  {name:20s} {imp:>5d}  {bar}")

    path = trainer.save(output_dir=args.output_dir)
    print(f"\nModel saved to: {path}")


if __name__ == "__main__":
    main()
