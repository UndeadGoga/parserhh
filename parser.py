import requests
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)

def parse_vacancies(keyword):
    url = f"https://api.hh.ru/vacancies?text={keyword}"
    response = requests.get(url)
    logging.info(f"Request to {url} returned status code {response.status_code}")
    if response.status_code != 200:
        logging.error("Failed to fetch the vacancies page")
        return []

    vacancies = response.json().get('items', [])
    logging.info(f"Parsed {len(vacancies)} vacancies from API")

    parsed_vacancies = []
    for vacancy in vacancies:
        title = vacancy.get('name')
        company = vacancy.get('employer', {}).get('name')
        description = vacancy.get('snippet', {}).get('responsibility') or ''
        city = vacancy.get('area', {}).get('name', 'Не указан') if vacancy.get('area') else 'Не указан'
        salary = vacancy.get('salary', {}).get('amount') if vacancy.get('salary') else None

        parsed_vacancies.append({
            'title': title,
            'company': company,
            'description': description,
            'city': city,
            'salary': salary
        })

    return parsed_vacancies

def save_vacancies_to_db(vacancies, conn):
    with conn.cursor() as cur:
        for vacancy in vacancies:
            city = vacancy['city'] if vacancy['city'] is not None else 'Не указан'
            salary = vacancy['salary'] if vacancy['salary'] is not None else None

            cur.execute("""
                INSERT INTO vacancies (title, company, description, city, salary) 
                VALUES (%s, %s, %s, %s, %s)
            """, (
                vacancy['title'],
                vacancy['company'],
                vacancy['description'],
                city,
                salary
            ))
    conn.commit()
    logging.info(f"Saved {len(vacancies)} vacancies to the database")



def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname='vacancies_db',
            user='postgres',
            password='1324',
            host='host.docker.internal'
        )
        logging.info("Database connection established")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Error connecting to database: {e}")
        raise
