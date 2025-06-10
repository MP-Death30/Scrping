from pymongo import MongoClient


CHAÎNE_DE_CONNEXION = "mongodb+srv://test:123@cluster0.dtgdmge.mongodb.net/Scraping"
client = MongoClient(CHAÎNE_DE_CONNEXION)

db = client.Scraping

p = {
    'prenom': 'test',
    'nom': 'Test'
}

result = db.articles.insert_one(p)

print(result)