from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, ConversationHandler
import psycopg2
import logging
from parser import parse_vacancies, save_vacancies_to_db, get_db_connection

logging.basicConfig(level=logging.INFO)

SEARCH_VACANCY = range(1)

# Объявление клавиатуры
reply_keyboard = [['Старт', 'Вакансии']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Добро пожаловать! Выберите действие:',
        reply_markup=markup
    )

async def start_info(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Добро пожаловать! Используйте /vacancies, чтобы искать вакансии.',
        reply_markup=markup
    )

async def start_vacancies(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите вакансию:', reply_markup=ReplyKeyboardRemove())
    return SEARCH_VACANCY

def check_vacancies_in_db(conn, keyword):
    with conn.cursor() as cur:
        try:
            logging.info("Выполняется запрос SELECT для проверки вакансий")
            cur.execute(
                "SELECT title, company, description, city, salary FROM vacancies WHERE title ILIKE %s OR description ILIKE %s",
                (f'%{keyword}%', f'%{keyword}%'))
            vacancies = cur.fetchall()
            logging.info(f"Найдено {len(vacancies)} вакансий в базе данных.")
            return vacancies
        except Exception as e:
            logging.error(f"Ошибка при получении вакансий из базы данных: {e}")
            raise

def save_unique_vacancies_to_db(vacancies, conn, keyword):
    with conn.cursor() as cur:
        for vacancy in vacancies:
            cur.execute("SELECT id FROM vacancies WHERE title = %s AND company = %s AND description = %s",
                        (vacancy['title'], vacancy['company'], vacancy['description']))
            if not cur.fetchone():
                cur.execute("INSERT INTO vacancies (title, company, description, city, salary) VALUES (%s, %s, %s, %s, %s)",
                            (vacancy['title'], vacancy['company'], vacancy['description'], vacancy['city'], vacancy['salary']))
    conn.commit()

async def vacancies(update: Update, context: CallbackContext) -> None:
    keyword = update.message.text.strip()
    if not keyword:
        await update.message.reply_text('Пожалуйста, укажите ключевое слово для поиска вакансий.', reply_markup=markup)
        return SEARCH_VACANCY
    try:
        conn = get_db_connection()
        logging.info(f"Поиск вакансий с ключевым словом: {keyword}")
        existing_vacancies = check_vacancies_in_db(conn, keyword)

        if not existing_vacancies:
            logging.info("В базе данных вакансий не найдено, начинается парсинг")
            new_vacancies = parse_vacancies(keyword)
            logging.info(f"Найдено {len(new_vacancies)} новых вакансий через парсинг")
            save_unique_vacancies_to_db(new_vacancies, conn, keyword)
            existing_vacancies = check_vacancies_in_db(conn, keyword)
        if existing_vacancies:
            await update.message.reply_text(f'Найдено {len(existing_vacancies)} вакансий:', reply_markup=markup)
            for vacancy in existing_vacancies:
                title = vacancy[0]
                company = vacancy[1]
                description = vacancy[2]
                city = vacancy[3]
                salary = vacancy[4]

                description_clean = description.replace('<highlighttext>', '').replace('</highlighttext>', '')

                response = (
                    f"Название: {title}\n"
                    f"Компания: {company}\n"
                    f"Описание: {description_clean}\n"
                    f"Город: {city}\n"
                    f"Зарплата: {salary}\n\n"
                )
                await update.message.reply_text(response, reply_markup=markup)
        else:
            await update.message.reply_text('Вакансий не найдено.', reply_markup=markup)
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text('Произошла ошибка при обработке вашего запроса.', reply_markup=markup)
    return ConversationHandler.END

async def menu_selection(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if text == 'Старт':
        await start_info(update, context)
    elif text == 'Вакансии':
        await start_vacancies(update, context)
    else:
        await update.message.reply_text('Пожалуйста, используйте кнопки для навигации.', reply_markup=markup)

def main() -> None:
    app = ApplicationBuilder().token("7447866613:AAFJpPQ4RlloPsyzGHkr9lez5WFm21xepVA").build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(Вакансии)$'), start_vacancies)],
        states={
            SEARCH_VACANCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, vacancies)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex('^(Старт|Вакансии)$'), menu_selection))

    app.run_polling()

if __name__ == '__main__':
    main()
