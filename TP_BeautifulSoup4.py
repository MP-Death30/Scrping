import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient


CHAÎNE_DE_CONNEXION = "mongodb+srv://test:123@cluster0.dtgdmge.mongodb.net/Scraping"
client = MongoClient(CHAÎNE_DE_CONNEXION)

db = client.Scraping



def fetch_articles(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')


        main_tag = soup.find('main')
        if not main_tag:
            print("No <main> tag found.")
            return []

        articles = main_tag.find_all('article')
        for article in articles:
            img_div = article.find(
                'div',
                class_='post-thumbnail picture rounded-img'
            )

            # URL Image principale
            img_tag = img_div.find('img') if img_div else None
            img_url = extract_img_url(img_tag)

            meta_div = article.find(
                'div',
                class_='entry-meta ms-md-5 pt-md-0 pt-3'
            )

            # Tag principal
            tag = (meta_div.find('span', class_='favtag color-b')
                       .get_text(strip=True)
                   ) if meta_div else None
            
            # Date
            date = (meta_div.find('time', class_='entry-date')
                        .get("datetime")[0:10]
                   ) if meta_div else None

            header = (meta_div.find('header', class_='entry-header pt-1')
                      ) if meta_div else None
            a_tag = header.find('a') if header else None
            
            # URL de l'article
            article_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else None
            
            # Titre
            title = (a_tag.find('h3').get_text(strip=True)
                     ) if a_tag and a_tag.find('h3') else None

            
            # Résumé
            summary_div = (meta_div.find('div', class_='entry-excerpt t-def t-size-def pt-1')
                           ) if meta_div else None
            summary = summary_div.get_text(strip=True) if summary_div else None


            # Utilisation URL de l'article
            dans_article = fetch_article(article_url)




            # Finalisation
            article_data = {
                'image': img_url,
                'tag': tag,
                'date': date,
                'url': article_url,
                'title': title,
                'summary': summary,
                'subtag': dans_article
            }
            articles_data.append(article_data)


        return articles_data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

# Dans l'article
def fetch_article(url):
    in_article = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Sous-catégorie
        tags_ul = soup.find('ul', class_='tags-list')
        subtags = []
        if tags_ul:
            links = tags_ul.find_all('a', class_='post-tags')
            for a in links:
                subtags.append(a.get_text(strip=True))


        # Nom de l'auteur
        author_span = soup.find('span', class_='byline')
        author = author_span.get_text(strip=True) if author_span else None

        # Images de l'article
        content_div = soup.find('div', class_='entry-content')
        figures = {}
        if content_div:
          figure_tags = content_div.find_all('figure')
          for idx, fig in enumerate(figure_tags, start=1):
              a_tag = fig.find('a')
              caption_tag = fig.find('figcaption')

              img_url = None
              if a_tag and a_tag.has_attr('href'):
                  href = a_tag['href']
                  if href.startswith('http://') or href.startswith('https://'):
                      img_url = href

              caption = caption_tag.get_text(strip=True) if caption_tag else None

              if img_url:
                  figures[f'image_{idx}'] = {
                      'url': img_url,
                      'caption': caption
                  }


        # Textes
        content_div = soup.find('div', class_='entry-content')
        texts_ordered = ""
        if content_div:
            tags = content_div.find_all(['h2', 'h3', 'p'])
            texts_list = [tag.get_text(strip=True) for tag in tags]
            texts_ordered = "\n".join(texts_list)



        # Finalisation
        in_article.append({
            'subtag': subtags,
            'author': author,
            'figures': figures,
            'texts_ordered': texts_ordered
        })

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

    return in_article

  



def extract_img_url(img_tag):
  if not img_tag:
      return None
  url_attributes = [
      'data-lazy-src',
      'data-src',
      'src'
  ]
  for attr in url_attributes:
    if img_tag.has_attr(attr):
      url = img_tag[attr]
      if url and url.startswith('https://'):
        return url
  return None


# ======== Parcourir toutes les pages ========
num_page = 1
max_num_page = 1  # À modifier selon besoin

while num_page <= max_num_page:
    url = f"https://www.blogdumoderateur.com/web/page/{num_page}"
    raw_articles = fetch_articles(url)
    
    for article in raw_articles:
        if not article['subtag']:
            continue

        # Extraction des infos de l'article
        subtag_data = article['subtag'][0]

        formatted_article = {
            'title': article.get('title'),
            'author': subtag_data.get('author'),
            'image': article.get('image'),
            'date': article.get('date'),
            'tag': article.get('tag'),
            'summary': article.get('summary'),
            'subtag': subtag_data.get('subtag'),
            'texts_ordered': subtag_data.get('texts_ordered'),
            'figures': subtag_data.get('figures')
        }

        # Insertion dans MongoDB
        db.articles.insert_one(formatted_article)

    num_page += 1