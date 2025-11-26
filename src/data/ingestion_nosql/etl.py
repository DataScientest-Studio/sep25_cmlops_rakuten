import pandas as pd
from pymongo import MongoClient
import html
import re

# ---------- nettoyage minimal ----------
def clean_text(text):
    if not isinstance(text, str):
        if pd.isna(text):
            return ""
        text = str(text)
    # supprimer balises HTML
    text = re.sub(r"<[^>]+>", "", text)
    # décoder entités HTML
    text = html.unescape(text)
    return text.strip()

# ---------- ETL ----------
csv_path = "/mnt/c/Users/guill/Downloads/X_train_update.csv"
csv_path_y = "/mnt/c/Users/guill/Downloads/Y_train_CVw08PX.csv"

# 1) extraction
df = pd.read_csv(csv_path)
print ("Taille csv :", len(df))
df = df.rename(columns={df.columns[0]: "idx"})
df_y = pd.read_csv(csv_path_y)
print ("Taille csv_y :", len(df_y))
df_y = df_y.rename(columns={df_y.columns[0]: "idx"})
df = df.merge(df_y, on="idx", how="left")

# 2) colonnes utiles
colonnes_utiles = ["productid", "designation", "description", "imageid","prdtypecode"]
colonnes_existant = [c for c in colonnes_utiles if c in df.columns]
df = df[colonnes_existant].copy()

# 3) nettoyage des textes
text_cols = ["designation", "description"]
for col in text_cols:
    if col in df.columns:
        df[col] = df[col].apply(clean_text)

# 4) chargement MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client["rakuten_db"]
collection = db["produits"]

collection.delete_many({})
collection.insert_many(df.to_dict("records"))

print(f"{len(df)} documents insérés, par ex. :")
print("--- HEAD ---")
print(df.head())
print("--- TAIL ---")
print(df.tail())