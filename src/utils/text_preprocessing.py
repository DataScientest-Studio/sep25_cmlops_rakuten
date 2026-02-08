"""
Text Preprocessing Utilities :
    - Removes (HTML, URLs, SKUs, IDs) to focus on semantic content.
    - Aggressive cleaning using pre-compiled Regex.
    - Usage:
        - `clean_text`: Low-level cleaner.
        - `input_text_train`: Bulk processing for DataFrames.
        - `input_text_infer`: Fast processing for API requests.
"""

import html
import re
from typing import Any

import pandas as pd

# Regex patterns
REGEX_HTML = re.compile(r"<[^>]+>")
REGEX_URL = re.compile(r"http[s]?://\S+|www\.\S+")
REGEX_EMAIL = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
REGEX_PRODUCT_REF = re.compile(
    r"\b(ref|réf|reference|référence|fabricant|model|modèle|sku|asin|ean|isbn|gtin)"
    r"[\s\.:_-]*[a-z0-9][a-z0-9\-_.]{2,}\b"
)
REGEX_CODE = re.compile(r"[a-zA-Z]{2,}-\d+(?:-[a-zA-Z]{2,})?")
REGEX_LONG_NUM = re.compile(r"\b\d{6,}\b")
REGEX_SPACES = re.compile(r"\s+")


def clean_text(text: str | Any = None) -> str:
    """Clean a single text field."""
    if text is None or pd.isna(text):
        return ""
    text = html.unescape(str(text)).lower()
    text = REGEX_HTML.sub(" ", text)
    text = REGEX_URL.sub(" ", text)
    text = REGEX_EMAIL.sub(" ", text)
    text = REGEX_PRODUCT_REF.sub(" ", text)
    text = REGEX_CODE.sub(" ", text)
    text = REGEX_LONG_NUM.sub(" ", text)
    text = REGEX_SPACES.sub(" ", text).strip()
    return text


def input_text_train(
    df: pd.DataFrame,
    col_des: str = "product_designation",
    col_desc: str = "product_description",
) -> pd.DataFrame:
    """Clean designation and description, build text_tr for training."""
    df["designation_tr"] = df[col_des].apply(clean_text)
    df["description_tr"] = df[col_desc].apply(clean_text)
    df["text_tr"] = (
        df["designation_tr"].str.cat(df["description_tr"], sep=" ").str.strip()
    )
    return df


def input_text_infer(designation: str, description: str | None = None) -> str:
    """Build unified text field for inference."""
    designation_clean = clean_text(designation)
    description_clean = clean_text(description)
    return (designation_clean + " " + description_clean).strip()
