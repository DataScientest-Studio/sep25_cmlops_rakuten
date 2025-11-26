import pickle
import html
import re
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================
# Chargement modèle
# =====================
model = joblib.load(os.path.join(BASE_DIR, "..", "model_prdtypecode_svm.joblib"))
vectorizer = joblib.load(os.path.join(BASE_DIR, "..", "tfidf_vectorizer.joblib"))

# =====================
# Nettoyage identique training.py
# =====================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()

# =====================
# Fonction prédiction réutilisable
# =====================
def predict_texts(raw_texts):
    texts = [clean_text(t) for t in raw_texts]
    X = vectorizer.transform(texts)
    preds = model.predict(X)

    result = {"predictions": [int(p) for p in preds]}

    if hasattr(model, "predict_proba"):
        result["probabilities"] = model.predict_proba(X).tolist()
        result["classes"] = [int(c) for c in getattr(model, "classes_", [])]

    return result