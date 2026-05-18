import json
import os

# Імпорт функцій з попередніх модулів
from parser import parse_rmpd_html
from ocr_by_api import extract_data_from_documents
from validator import validate_documents, print_validation_report
from sent_checker import check_hs_codes_against_sent, print_sent_report

def load_db(filename):
    # Завантаження JSON бази даних
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    print(f"Помилка: Файл бази {filename} не знайдено")
    return {}

def main():
    print("Запуск системи автоматизованої перевірки документів\n")

    RMPD_FILE = "RMPD20250125001873 (RMPD_110).html"
    CMR_FILE = "cmr.jpg"
    INVOICE_FILE = "invoice.jpg"

    if not os.path.exists(RMPD_FILE):
        print(f"Помилка: Файл декларації '{RMPD_FILE}' не знайдено.")
        return

    # Завантажуємо бази даних з JSON-файлів
    ecmt_db = load_db("ecmt_database.json")
    gps_db = load_db("gps_database.json")

    # Парсинг RMPD
    print(f"Парсинг декларації {RMPD_FILE}...")
    rmpd_data = parse_rmpd_html(RMPD_FILE)
    if not rmpd_data: return
    print("Дані з RMPD успішно отримано.\n")

    # Розпізнавання OCR
    print("Читання фотографій транспортних документів через AI Vision...")
    ocr_data = extract_data_from_documents(cmr_path=CMR_FILE, invoice_path=INVOICE_FILE)
    if not ocr_data: return
    print("Дані з документів успішно розпізнано.\n")

    # Валідація даних
    print(" Перевірка розбіжностей...")
    validation_report = validate_documents(rmpd_data, ocr_data, ecmt_db=ecmt_db, gps_db=gps_db)
    print_validation_report(validation_report)

    # Перевірка SENT
    print("\nПеревірка кодів по базі SENT...")
    hs_codes_from_invoice = ocr_data.get('hs_codes', [])
    print(f"Знайдені коди в документах: {hs_codes_from_invoice}")

    sent_report = check_hs_codes_against_sent(hs_codes_from_invoice)
    print_sent_report(sent_report)

    print("\nРоботу завершено.")

if __name__ == "__main__":
    main()