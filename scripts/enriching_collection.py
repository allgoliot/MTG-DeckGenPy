import pandas as pd
import requests
import time

# Charger ton CSV actuel
collection = pd.read_csv("collection.csv")

def fetch_scryfall_data(scryfall_id):
    url = f"https://api.scryfall.com/cards/{scryfall_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    print(f"Fetched data for {data.get('name', 'Unknown Card')}")
    return {
        "type_line": data.get("type_line"),
        "mana_value": data.get("cmc"),
        "colors": data.get("colors"),
        "color_identity": data.get("color_identity"),
        "oracle_text": data.get("oracle_text")
    }

# Ajouter colonnes vides
collection["type_line"] = ""
collection["mana_value"] = ""
collection["colors"] = ""
collection["color_identity"] = ""
collection["oracle_text"] = ""

# Enrichir
for index, row in collection.iterrows():
    scryfall_id = row["Scryfall ID"]
    card_data = fetch_scryfall_data(scryfall_id)
    
    if card_data:
        for key, value in card_data.items():
            collection.at[index, key] = str(value)
    #print(f"Enrichi {index + 1}/{len(collection)}: {row['name']}")
    
    time.sleep(0.1)  # éviter de spam l’API

# Sauvegarde
collection.to_csv("collection_enriched.csv", index=False)

print("Enrichissement terminé !")