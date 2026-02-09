"""Text feature extraction for Swedish real estate descriptions.

Provides a ``TextFeatureExtractor`` that wraps TF-IDF vectorization with
Swedish-specific preprocessing (stop words, domain-specific stop words,
lowercasing, and optional n-gram support).

Usage::

    extractor = TextFeatureExtractor.fit(descriptions)
    tfidf_matrix = extractor.transform(descriptions)
    extractor.save("models/text_features.joblib")

    loaded = TextFeatureExtractor.load("models/text_features.joblib")
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

_DOMAIN_STOP_WORDS = [
    # Generic real estate terms that appear in almost every listing
    "rum", "kvm", "m²", "bostadsrätt", "bostadsrättsförening",
    "lägenhet", "bostad", "brf", "förening", "avgift",
    "kr", "sek", "månad", "mån", "kvartal",
    "våning", "hiss", "balkong", "trappa", "trappor",
    # Agent boilerplate
    "välkommen", "visning", "mäklare", "kontakta", "anmälan",
    "budgivning", "intresseanmälan", "hemnet",
    "ansvarig", "fastighetsmäklare", "boka", "information",
    "mer", "ring", "maila", "mail",
    # Common filler
    "finns", "samt", "även", "till", "från", "inom",
    "här", "denna", "detta", "dessa", "vara", "blir",
    "kan", "har", "mycket", "stor", "stora", "liten", "lilla",
    "bor", "bra", "fin", "fina", "fint", "nya", "nytt",
]

# Regex patterns for agent boilerplate sections at the end of descriptions
_AGENT_BOILERPLATE_RE = re.compile(
    r"(ansvarig\s+(?:fastighetsmäklare|mäklare)\s*:?\s*.{0,120}$"
    r"|för\s+mer\s+information\s*.{0,200}$"
    r"|kontakta\s+.{0,100}$"
    r"|välkommen\s+(?:på\s+)?visning.{0,200}$"
    r"|ring\s+eller\s+maila.{0,100}$)",
    flags=re.IGNORECASE | re.DOTALL,
)


def _load_swedish_stop_words() -> list[str]:
    """Load Swedish stop words from NLTK, falling back to a minimal set."""
    try:
        from nltk.corpus import stopwords
        return stopwords.words("swedish")
    except (ImportError, LookupError):
        logger.warning("NLTK Swedish stop words unavailable — using minimal set")
        return [
            "och", "det", "att", "i", "en", "jag", "hon", "som", "han", "på",
            "den", "med", "var", "sig", "för", "inte", "men", "av", "om", "hade",
            "de", "till", "är", "vi", "ett", "min", "nu", "så", "mot", "vid",
        ]


class TextFeatureExtractor:
    """TF-IDF feature extractor for Swedish property descriptions."""

    def __init__(
        self,
        max_features: int = 2000,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 3,
        max_df: float = 0.85,
        sublinear_tf: bool = True,
        extra_stop_words: Optional[list[str]] = None,
    ) -> None:
        all_stop_words = (
            _load_swedish_stop_words()
            + _DOMAIN_STOP_WORDS
            + (extra_stop_words or [])
        )
        # Deduplicate and lowercase
        self._stop_words = sorted(set(w.lower() for w in all_stop_words))

        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            sublinear_tf=sublinear_tf,
            stop_words=self._stop_words,
            strip_accents=None,  # Keep Swedish chars (å ä ö)
            token_pattern=r"(?u)\b[a-zåäöA-ZÅÄÖ]{2,}\b",
        )
        self._is_fitted = False

    @staticmethod
    def preprocess(text: str) -> str:
        """Clean a single description string."""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)  # strip HTML tags
        text = re.sub(r"https?://\S+", " ", text)  # strip URLs
        text = _AGENT_BOILERPLATE_RE.sub("", text)  # strip agent boilerplate
        text = re.sub(r"\d[\d\s]*(?:kr|sek|m²|kvm)", " ", text, flags=re.I)  # strip prices/areas
        text = re.sub(r"\b\d+\b", " ", text)  # strip standalone numbers
        text = re.sub(r"[^\wåäöÅÄÖ\s]", " ", text)  # keep letters + Swedish chars
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def fit(self, descriptions: list[str]) -> "TextFeatureExtractor":
        """Fit the TF-IDF vocabulary on a corpus of descriptions."""
        cleaned = [self.preprocess(d) for d in descriptions]
        self._vectorizer.fit(cleaned)
        self._is_fitted = True
        logger.info(
            "Fitted TF-IDF: %d features from %d documents",
            len(self._vectorizer.vocabulary_),
            len(cleaned),
        )
        return self

    def transform(self, descriptions: list[str]) -> csr_matrix:
        """Transform descriptions to TF-IDF matrix."""
        if not self._is_fitted:
            raise RuntimeError("Call fit() before transform()")
        cleaned = [self.preprocess(d) for d in descriptions]
        return self._vectorizer.transform(cleaned)

    def fit_transform(self, descriptions: list[str]) -> csr_matrix:
        """Fit and transform in one step."""
        cleaned = [self.preprocess(d) for d in descriptions]
        matrix = self._vectorizer.fit_transform(cleaned)
        self._is_fitted = True
        logger.info(
            "Fitted TF-IDF: %d features from %d documents",
            len(self._vectorizer.vocabulary_),
            len(cleaned),
        )
        return matrix

    @property
    def feature_names(self) -> list[str]:
        return self._vectorizer.get_feature_names_out().tolist()

    @property
    def vocabulary_size(self) -> int:
        if not self._is_fitted:
            return 0
        return len(self._vectorizer.vocabulary_)

    @property
    def stop_words(self) -> list[str]:
        return self._stop_words

    def top_features_for_document(
        self, text: str, n: int = 20
    ) -> list[tuple[str, float]]:
        """Return the top-N TF-IDF features for a single document."""
        vec = self.transform([text])
        scores = vec.toarray().flatten()
        names = self.feature_names
        top_idx = np.argsort(scores)[::-1][:n]
        return [(names[i], float(scores[i])) for i in top_idx if scores[i] > 0]

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"vectorizer": self._vectorizer, "stop_words": self._stop_words},
            path,
        )
        logger.info("Saved TextFeatureExtractor to %s", path)

    @classmethod
    def load(cls, path: Path | str) -> "TextFeatureExtractor":
        data = joblib.load(path)
        obj = cls.__new__(cls)
        obj._vectorizer = data["vectorizer"]
        obj._stop_words = data["stop_words"]
        obj._is_fitted = True
        logger.info("Loaded TextFeatureExtractor from %s", path)
        return obj
