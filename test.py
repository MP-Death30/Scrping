import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


def input_non_empty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Ce champ est obligatoire, merci de le renseigner.")


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


def get_user_inputs():
    print("🔎 Saisie des critères de recherche :")

    query = input_non_empty("Requête médicale (ex: dermatologue, généraliste) : ")

    # Dates obligatoires
    while True:
        start_date_str = input_non_empty("Date début de disponibilité (JJ/MM/AAAA) : ")
        start_date = parse_date(start_date_str)
        if not start_date:
            print("Format de date invalide. Réessayez.")
            continue

        end_date_str = input_non_empty("Date fin de disponibilité (JJ/MM/AAAA) : ")
        end_date = parse_date(end_date_str)
        if not end_date:
            print("Format de date invalide. Réessayez.")
            continue

        if end_date < start_date:
            print("La date de fin doit être supérieure ou égale à la date de début.")
            continue
        break

    address = input_non_empty("Adresse ou mot-clé géographique : ")

    # Optionnels
    max_results_str = input("Nombre max de résultats (par défaut 10) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10

    secteur = input("Type d’assurance (1, 2, non conventionné) [optionnel] : ").strip().lower()
    consultation = input("Type de consultation (visio, cabinet, les deux) [optionnel] : ").strip().lower()
    if consultation not in ("visio", "cabinet", "les deux"):
        consultation = "les deux"

    prix_min_str = input("Prix minimum (€) [optionnel] : ").strip()
    prix_max_str = input("Prix maximum (€) [optionnel] : ").strip()
    prix_min = float(prix_min_str) if prix_min_str.replace('.', '', 1).isdigit() else 0
    prix_max = float(prix_max_str) if prix_max_str.replace('.', '', 1).isdigit() else 1000

    return {
        "query": query,
        "start_date": start_date,
        "end_date": end_date,
        "address": address,
        "max_results": max_results,
        "secteur": secteur,
        "consultation": consultation,
        "prix_min": prix_min,
        "prix_max": prix_max,
    }


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrap_doctolib(filters):
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    url = "https://www.doctolib.fr/"
    driver.get(url)

    try:
        wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-disagree-button"))).click()
    except:
        pass

    # Recherche spécialité
    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchbar-input.searchbar-query-input")))
    search_input.clear()
    search_input.send_keys(filters["query"])
    time.sleep(1)

    # Recherche lieu
    place_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Lieu']")
    place_input.clear()
    place_input.send_keys(filters["address"])
    place_input.send_keys(Keys.ENTER)

    # Attente résultats
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-test='search-result']")))
    time.sleep(2)

    doctors = driver.find_elements(By.CSS_SELECTOR, "div[data-test='search-result']")[:filters["max_results"]]
    data = []

    for doc in doctors:
        try:
            name = doc.find_element(By.CSS_SELECTOR, "h3").text.strip()
            next_slot = doc.find_element(By.CSS_SELECTOR, "[data-test='next-availability']").text.strip()
            address = doc.find_element(By.CSS_SELECTOR, "[data-test='address']").text.strip()

            # Filtrer par période de dispo (simple filtrage texte ici, Doctolib ne donne pas de date directe)
            # Tu peux améliorer ici pour parse et comparer date précise si nécessaire

            # Type consultation (visio ou cabinet)
            consult_type = "visio" if "vidéo" in doc.text.lower() else "cabinet"

            price = None
            try:
                price_info = doc.find_element(By.CSS_SELECTOR, "[data-test='price']").text.strip()
                price = int(''.join(filter(str.isdigit, price_info)))
            except:
                price = None

            sector = "inconnu"
            try:
                sector = doc.find_element(By.CSS_SELECTOR, "[data-test='sector']").text.strip().lower()
            except:
                pass

            # Filtres optionnels
            if filters["secteur"] and filters["secteur"] not in sector:
                continue
            if filters["consultation"] != "les deux" and consult_type != filters["consultation"]:
                continue
            if price is not None and (price < filters["prix_min"] or price > filters["prix_max"]):
                continue

            # Adresse décomposée
            parts = address.split("\n")
            rue = parts[0] if len(parts) > 0 else ""
            code_postal = ""
            ville = ""
            if len(parts) > 1:
                tokens = parts[1].split(" ")
                if len(tokens) > 1:
                    code_postal = tokens[0]
                    ville = " ".join(tokens[1:])

            data.append({
                "Nom complet": name,
                "Prochaine disponibilité": next_slot,
                "Type de consultation": consult_type,
                "Secteur": sector,
                "Prix (€)": price if price else "NC",
                "Adresse": rue,
                "Code postal": code_postal,
                "Ville": ville
            })

        except Exception as e:
            print("⚠️ Erreur sur un médecin :", e)
            continue

    driver.quit()
    return data


def export_csv(data, filename="resultats_medecins.csv"):
    if not data:
        print("Aucune donnée à exporter.")
        return
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ Données exportées vers {filename}")


if __name__ == "__main__":
    filters = get_user_inputs()
    results = scrap_doctolib(filters)
    export_csv(results)
