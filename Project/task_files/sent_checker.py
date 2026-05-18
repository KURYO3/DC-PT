import requests
import io
import re
from PyPDF2 import PdfReader

# Актуальне посилання на список товарів SENT
SENT_PDF_URL = "https://puesc.gov.pl/documents/20123/623158810/EN+-+WYKAZ+TOWAR%C3%93W+-+CN+od+20220427.pdf/fd0cf0c3-44d7-78bf-1dd5-cd0a538c35b3?t=1676292368762"

def fetch_sent_codes(url):
    # Завантажує PDF у буфер, витягує весь текст і за допомогою регулярних виразів знаходить усі товарні коди CN
    print("Завантаження актуальної таблиці SENT з офіційного сайту...")
    try:
        # Завантажуємо файл у буфер пам'яті (без збереження на диск)
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)

        # Читаємо PDF з пам'яті
        reader = PdfReader(pdf_file)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        # Регулярний вираз для пошуку кодів (напр.: 0207, ex 0409 00 00, 2710)
        # Шукає 4 цифри, за якими можуть йти ще пари цифр через пробіл
        pattern = r'(?:ex\s*)?(\d{4}(?:\s\d{2}){0,2})\b'
        matches = re.findall(pattern, full_text)

        sent_codes = set()
        for match in matches:
            # Очищаємо код від пробілів (напр. 0811 10 -> 081110)
            clean_code = match.replace(" ", "")
            if len(clean_code) >= 4:
                sent_codes.add(clean_code)

        print(f"Успішно завантажено та розпізнано {len(sent_codes)} унікальних кодів SENT.")
        return list(sent_codes)

    except Exception as e:
        print(f"Помилка під час завантаження або обробки PDF: {e}")
        return []

def clean_hs_code(code):
    # Очищає розпізнаний HS код від пробілів, крапок тощо
    if not code:
        return ""
    return str(code).replace(" ", "").replace(".", "").strip()

def check_hs_codes_against_sent(ocr_hs_codes, pdf_url=SENT_PDF_URL):
    # Перевіряє, чи підпадають знайдені в документах коди під дію системи SENT
    if not ocr_hs_codes:
        return {"status": "Немає кодів для перевірки", "flagged": []}

    # Завантажуємо актуальний список кодів
    sent_codes = fetch_sent_codes(pdf_url)
    if not sent_codes:
        return {"status": "Помилка завантаження кодів SENT", "flagged": []}

    flagged_codes = []

    # Перевіряємо кожен код з документів
    for raw_code in ocr_hs_codes:
        code = clean_hs_code(raw_code)
        if not code:
            continue

        # Якщо код з документів (напр. 27101981) починається з будь-якого коду SENT (напр. 2710), то це ризиковий товар.
        is_flagged = False
        matched_sent_rule = None

        for sent_code in sent_codes:
            if code.startswith(sent_code):
                is_flagged = True
                matched_sent_rule = sent_code
                break

        if is_flagged:
            flagged_codes.append({
                "invoice_code": raw_code,
                "reason": f"Підпадає під групу SENT: {matched_sent_rule}"
            })

    # Формування результатів
    if flagged_codes:
        return {"status": "Виявлено товари SENT", "flagged": flagged_codes}
    else:
        return {"status": "Товарів SENT не виявлено", "flagged": []}

def print_sent_report(sent_report):
    # Звіт про перевірку SENT
    print("\n Звіт перевірки кодів SENT ")
    print(f"Статус: {sent_report['status']}")

    if sent_report['flagged']:
        print("\nСписок кодів, що потребують додаткової декларації:")
        for item in sent_report['flagged']:
            print(f" Код з документа: {item['invoice_code']} ({item['reason']})")