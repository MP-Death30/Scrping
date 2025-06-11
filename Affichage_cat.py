from pymongo import MongoClient

client = MongoClient("mongodb+srv://test:123@cluster0.dtgdmge.mongodb.net/Scraping")
db = client.Scraping
collection = db.articles

def get_articles_by_tag(tag=None, subtag=None):
    query = {}
    if tag:
        query['tag'] = tag
    if subtag:
        query['subtag'] = subtag  # subtag est une liste

    articles = collection.find(query)
    results = list(articles)

    if not results:
        print("Aucun article trouvé.")
        return

    for article in results:
        print(f"Title: {article.get('title')}")
        print(f"Author: {article.get('author')}")
        print(f"Date: {article.get('date')}")
        print(f"Tag: {article.get('tag')}")
        print(f"Subtags: {article.get('subtag')}")
        print("="*40)


# === Interaction avec l'utilisateur ===

print("Souhaitez-vous rechercher par catégorie (tag) ou sous-catégorie (subtag) ?")
choix = input("Entrez 'tag' ou 'subtag' : ").strip().lower()

if choix not in ['tag', 'subtag']:
    print("Choix invalide. Veuillez relancer le programme.")
else:
    valeur = input(f"Entrez la valeur de {choix} : ").strip()
    if choix == 'tag':
        get_articles_by_tag(tag=valeur)
    else:
        get_articles_by_tag(subtag=valeur)