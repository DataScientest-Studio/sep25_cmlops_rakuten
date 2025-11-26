# training.py
# -*- coding: utf-8 -*-
import re
import unicodedata
from pymongo import MongoClient
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "..", "model")

# stopwords
try:
    fr_stop = stopwords.words('french')
except LookupError:
    nltk.download('stopwords')
    fr_stop = stopwords.words('french')

def preprocess_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'<[^>]*>', ' ', text)
    text = unicodedata.normalize('NFD', text)
    text = "".join([ch for ch in text if unicodedata.category(ch) != 'Mn'])
    text = re.sub(r'\d+', '0', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def train_model(mongo_uri="mongodb://localhost:27017",
                db_name="rakuten_db",
                collection_name="produits"):
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]

    data_list = list(collection.find({}))
    df = pd.DataFrame(data_list)

    if 'designation' not in df.columns or 'prdtypecode' not in df.columns:
        raise KeyError("Champs 'designation' et 'prdtypecode' requis.")

    df['description'] = df.get('description', pd.Series(dtype=str)).fillna("")
    df['text'] = (df['designation'].fillna("") + " " + df['description'].fillna("")).apply(preprocess_text)

    X_texts = df['text'].values
    y = df['prdtypecode'].values.astype(str)

    X_train, X_val, y_train, y_val = train_test_split(
        X_texts, y, test_size=0.1, stratify=y, random_state=42
    )

    tfidf = TfidfVectorizer(
        strip_accents=None,
        lowercase=False,
        ngram_range=(1, 2),
        min_df=3,
        stop_words=fr_stop
    )

    X_train_tfidf = tfidf.fit_transform(X_train)
    X_val_tfidf = tfidf.transform(X_val)

    clf = LinearSVC(C=1.0, max_iter=10000)
    clf.fit(X_train_tfidf, y_train)

    y_pred = clf.predict(X_val_tfidf)
    report = classification_report(y_val, y_pred, output_dict=True)

    joblib.dump(clf, os.path.join(MODEL_DIR, "model_prdtypecode_svm.joblib"))
    joblib.dump(tfidf, os.path.join(MODEL_DIR, "tfidf_vectorizer.joblib"))

    return {"evaluation": report, "saved_files": ["model_prdtypecode_svm.joblib", "tfidf_vectorizer.joblib"]}

if __name__ == "__main__":
    # s'assure que le dossier existe (même si tu l'as déjà créé à la main, ça ne fera pas d'erreur)
    os.makedirs(MODEL_DIR, exist_ok=True)

    result = train_model()
    print("Fichiers sauvegardés :", result["saved_files"])