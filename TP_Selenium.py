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
        print("Ce champ est obligatoire.")


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


def get_user_inputs():
    print("Saisie des critères de recherche :")
    query = input_non_empty("Spécialité (ex: généraliste) : ")
    address = input_non_empty("Code postal ou ville : ")

    while True:
        start_date_str = input_non_empty("Date de début (JJ/MM/AAAA) : ")
        start_date = parse_date(start_date_str)
        if not start_date:
            print("Format invalide.")
            continue

        end_date_str = input_non_empty("Date de fin (JJ/MM/AAAA) : ")
        end_date = parse_date(end_date_str)
        if not end_date:
            print("Format invalide.")
            continue

        if end_date < start_date:
            print("La fin doit être après le début.")
            continue
        break

    max_results_str = input("Nombre max de résultats (défaut = 10) : ").strip()
    max_results = int(max_results_str) if max_results_str.isdigit() else 10

    return {
        "query": query,
        "address": address,
        "start_date": start_date,
        "end_date": end_date,
        "max_results": max_results
    }


def create_driver():
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ========================= ne pas toucher fonctionne ===================================
def rechercher_medecins(filters):
    driver = create_driver()
    wait = WebDriverWait(driver, 15)
    driver.get("https://www.doctolib.fr/")
    time.sleep(2)
    try:
        wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-disagree-button"))).click()
    except:
        pass

    # Saisie de la spécialité
    time.sleep(2)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchbar-input.searchbar-query-input")))
    search_input = driver.find_element(By.CSS_SELECTOR, "input.searchbar-input.searchbar-query-input")
    search_input.clear()
    search_input.send_keys(filters["query"])
    time.sleep(2)
    search_input.send_keys(Keys.TAB)

    # Saisie du lieu
    place_input = driver.find_element(By.CSS_SELECTOR, "input.searchbar-input.searchbar-place-input")
    place_input.clear()
    place_input.send_keys(filters["address"])
    time.sleep(2)
    place_input.send_keys(Keys.TAB)

    # Lancer recherche
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.searchbar-submit-button"))).click()
    time.sleep(2)

    results = []
    current_page = 1

    while len(results) < filters["max_results"]:
        time.sleep(2)
        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-design-system-component='Card']")

        for card in cards:
            try:
                # Nom et lien
                name = card.find_element(By.TAG_NAME, "h2").text.strip()
                link = card.find_element(By.TAG_NAME, "a").get_attribute("href")

                # Texte de non disponibilité
                try:
                    card.find_element(By.XPATH, ".//*[contains(text(), 'Aucune disponibilité en ligne') or contains(text(), 'réserve la prise de rendez-vous')]")
                    print(f"Médecin exclu (indisponible) : {name}")
                    continue
                except:
                    pass

                # Visio (si icône présente)
                visio_icon = card.find_elements(By.CSS_SELECTOR, "svg[data-icon-name='solid/video']")
                visio_available = len(visio_icon) > 0

                # Ajout au tableau
                results.append({
                    "nom_complet": name,
                    "lien": link,
                    "conventionnement": "NC",  # Conventionnement non filtré
                    "visio": visio_available
                })

                if len(results) >= filters["max_results"]:
                    break

            except Exception as e:
                print(f"Erreur sur une carte : {e}")
                continue

        # Si résultats suffisants ou pas de bouton page suivante, on quitte
        if len(results) >= filters["max_results"]:
            break

        try:
            next_button = driver.find_element(By.XPATH, "//a[.//span[contains(text(),'Page suivante')]]")
            next_button.click()
            time.sleep(2)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-design-system-component='Card']")))
            current_page += 1
        except:
            print("Fin des pages ou bouton 'Page suivante' non trouvé.")
            break

    driver.quit()
    return results


# ==============================================================================================================

def extraire_infos_medecin(driver, url):
    wait = WebDriverWait(driver, 10)
    driver.get(url)
    time.sleep(2)
    
    result = {
        "tarifs": "NC"
    }
    # ========================= ne pas toucher fonctionne ===================================
    try:
        # Attendre que les éléments de tarifs soient présents
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.dl-profile-text.dl-profile-fee")))
        tarifs_elements = driver.find_elements(By.CSS_SELECTOR, "div.dl-profile-text.dl-profile-fee")
        
        tarifs = []
        for el in tarifs_elements:
            try:
                nom_tarif = el.find_element(By.CSS_SELECTOR, "span.dl-profile-fee-name").get_attribute("textContent").strip()
                prix_tarif = el.find_element(By.CSS_SELECTOR, "span.dl-profile-fee-tag").get_attribute("textContent").strip()
                tarifs.append(f"{nom_tarif}: {prix_tarif}")
            except Exception as inner_e:
                pass
        
        if tarifs:
            result["tarifs"] = ", ".join(tarifs)
    
    except Exception as e:
        pass

    return result



def export_csv(data, filename="resultats_medecins.csv"):
    if not data:
        print("Aucune donnée à exporter.")
        return
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys(), delimiter=';')
        writer.writeheader()
        writer.writerows(data)
    print(f"Données exportées dans : {filename}")



def main():
    filters = get_user_inputs()
    medecins = rechercher_medecins(filters)
    print(f"{len(medecins)} médecins trouvés.")

    driver = create_driver()
    full_data = []

    for med in medecins[:filters["max_results"]]:
        print(f"Infos de {med['nom_complet']}...")
        infos = extraire_infos_medecin(driver, med["lien"])
        full_data.append({**med, **infos})

    driver.quit()

    if full_data:
        export_csv(full_data)
        print(full_data[0])
    else:
        print("Aucune donnée à exporter.")


if __name__ == "__main__":
    main()
