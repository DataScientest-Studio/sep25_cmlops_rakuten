"""
Text Feature Engineering

TF-IDF feature extraction for product text (designation + description).
"""
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.text_preprocessing import preprocess_text
import logging

logger = logging.getLogger(__name__)


class TextFeatureExtractor:
    """
    Extracts TF-IDF features from product text.

    Combines designation and description into a single text field,
    applies preprocessing, and transforms to TF-IDF features.
    """

    def __init__(
        self,
        max_features: int = 5000,
        ngram_range: tuple = (1, 2),
        min_df: int = 2,
        max_df: float = 0.95,
    ):
        """
        Initialize feature extractor.

        Args:
            max_features: Maximum number of features to extract
            ngram_range: N-gram range (e.g., (1,2) for unigrams and bigrams)
            min_df: Minimum document frequency
            max_df: Maximum document frequency (proportion)
        """
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            strip_accents="unicode",
            lowercase=True,
            stop_words="english",  # Basic English stopwords
        )

        logger.info(
            f"TextFeatureExtractor initialized: max_features={max_features}, "
            f"ngram_range={ngram_range}"
        )

    def fit(self, df: pd.DataFrame) -> "TextFeatureExtractor":
        """
        Fit vectorizer on training data.

        Args:
            df: DataFrame with 'designation' and 'description' columns

        Returns:
            self
        """
        texts = self._combine_texts(df)
        self.vectorizer.fit(texts)
        logger.info(f"Fitted vectorizer on {len(texts)} samples")
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform data to TF-IDF features.

        Args:
            df: DataFrame with 'designation' and 'description' columns

        Returns:
            TF-IDF feature matrix (numpy array or sparse matrix)
        """
        texts = self._combine_texts(df)
        features = self.vectorizer.transform(texts)
        logger.info(f"Transformed {len(texts)} samples to {features.shape[1]} features")
        return features

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fit and transform in one step.

        Args:
            df: DataFrame with 'designation' and 'description' columns

        Returns:
            TF-IDF feature matrix
        """
        texts = self._combine_texts(df)
        features = self.vectorizer.fit_transform(texts)
        logger.info(f"Fit and transformed {len(texts)} samples to {features.shape[1]} features")
        return features

    def _combine_texts(self, df: pd.DataFrame) -> list:
        """
        Combine designation and description into single text.

        Args:
            df: DataFrame with 'designation' and 'description' columns

        Returns:
            List of combined texts
        """
        texts = []
        for _, row in df.iterrows():
            designation = str(row.get("designation", ""))
            description = str(row.get("description", ""))

            # Preprocess each field
            designation_clean = preprocess_text(designation)
            description_clean = preprocess_text(description)

            # Combine with space
            combined = f"{designation_clean} {description_clean}"
            texts.append(combined)

        return texts

    def get_feature_names(self) -> list:
        """Get feature names (vocabulary)"""
        return self.vectorizer.get_feature_names_out().tolist()

    def save_vectorizer(self, path: str):
        """Save vectorizer to file"""
        import pickle

        with open(path, "wb") as f:
            pickle.dump(self.vectorizer, f)
        logger.info(f"Saved vectorizer to {path}")

    def load_vectorizer(self, path: str):
        """Load vectorizer from file"""
        import pickle

        with open(path, "rb") as f:
            self.vectorizer = pickle.load(f)
        logger.info(f"Loaded vectorizer from {path}")
