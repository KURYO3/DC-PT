import os
import json
import re
from google import genai
import PIL.Image

API_KEY = ""

def extract_data_from_documents(cmr_paths=None, invoice_paths=None):
    # Аналізує масив фотографій CMR та/або Інвойсів за допомогою Gemini 2.5 Flash. Повертає структурований словник з даними
    cmr_paths = cmr_paths or []
    invoice_paths = invoice_paths or []

    if not cmr_paths and not invoice_paths:
        print("Помилка: Необхідно вказати хоча б один документ (CMR або Invoice).")
        return None

    # Ініціалізація клієнта
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"Помилка ініціалізації API клієнта: {e}")
        return None

    contents = []

    # Промпт для моделі
    prompt = """
    Ти експерт з логістики та митного контролю. Проаналізуй надані зображення (CMR та/або Комерційний Інвойс).
    Витягни наступні дані та поверни їх у форматі суворого JSON.
    Якщо даних немає, використовуй null.

    ПРАВИЛА ВИБОРУ ДАНИХ (ПРИ НАЯВНОСТІ 2 ДОКУМЕНТІВ):
    1. Дані з CMR мають загальний пріоритет як основний транспортний документ.
    2. КРИТИЧНО ВАЖЛИВО (НАЗВИ ТА АДРЕСИ): НІКОЛИ НЕ ПЕРЕКЛАДАЙ текст самостійно! Якщо в CMR дані вказані українською/кирилицею, шукай точний англійський/латинський відповідник в Інвойсі.
    3. КРАЇНИ ТА МІСЦЯ ЗАВАНТАЖЕННЯ/РОЗВАНТАЖЕННЯ: Уважно дивись на поля 3 (Місце розвантаження / Place of delivery) та 4 (Місце та дата завантаження / Place of taking over) у CMR. Не бери ці локації з адрес відправника чи одержувача.

    Структура JSON:
    {
        "sender_name": "Точна назва компанії відправника (без перекладу)",
        "sender_address": {
            "street": "Вулиця та номер будинку",
            "postal_code": "Поштовий індекс",
            "city": "Місто",
            "country": "Країна"
        },
        "recipient_name": "Точна назва компанії одержувача",
        "recipient_address": {
            "street": "Вулиця та номер будинку",
            "postal_code": "Поштовий індекс",
            "city": "Місто",
            "country": "Країна"
        },
        "carrier_name": "Точна назва компанії перевізника",
        "carrier_address": {
            "street": "Вулиця та номер будинку",
            "postal_code": "Поштовий індекс",
            "city": "Місто",
            "country": "Країна"
        },
        "load_country": "Країна завантаження (з поля 4 CMR, код з 2 букв)",
        "unload_country": "Країна розвантаження (з поля 3 CMR, код з 2 букв)",
        "load_address": {
            "street": "Точна вулиця/місце завантаження (з поля 4 CMR)",
            "postal_code": "Поштовий індекс",
            "city": "Місто",
            "country": "Країна"
        },
        "unload_address": {
            "street": "Точна вулиця/місце розвантаження (з поля 3 CMR)",
            "postal_code": "Поштовий індекс",
            "city": "Місто",
            "country": "Країна"
        },
        "cmr_number": "Номер транспортного документа (CMR)",
        "truck_number": "Номерний знак тягача (без пробілів)",
        "trailer_number": "Номерний знак причепа (без пробілів)",
        "hs_codes": ["Список знайдених товарних кодів (HS code)"]
    }

    Важливо: Поверни ТІЛЬКИ валідний JSON без жодних вступних чи завершальних слів, без розмітки (```json).
    """
    contents.append(prompt)

    # Завантаження зображень з масивів
    try:
        for path in cmr_paths:
            if os.path.exists(path):
                contents.append(PIL.Image.open(path))
            else:
                print(f"Попередження: Файл CMR '{path}' не знайдено.")

        for path in invoice_paths:
            if os.path.exists(path):
                contents.append(PIL.Image.open(path))
            else:
                print(f"Попередження: Файл Інвойсу '{path}' не знайдено.")

    except Exception as e:
        print(f"Помилка відкриття зображень: {e}")
        return None

    if len(contents) == 1:  # Якщо додано тільки промпт, а картинки не завантажились
        return None

    print("Відправка запиту до Gemini...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )

        raw_text = response.text.strip()

        # Очищення від можливої markdown розмітки (```json ... ```)
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        # Парсинг JSON
        extracted_data = json.loads(raw_text)
        return extracted_data

    except json.JSONDecodeError:
        print("Помилка: Модель повернула некоректний JSON.")
        print("Відповідь моделі:", raw_text)
        return None
    except Exception as e:
        print(f"Помилка API Gemini: {e}")
        return None


if __name__ == "__main__":
    # Для тестування модуля
    TEST_CMR = "cmr.jpg"
    TEST_INVOICE = "invoice.jpg"

    print("Тестування модуля OCR:")

    # Можна передати тільки CMR, тільки Інвойс, або обидва
    result = extract_data_from_documents(cmr_paths=[TEST_CMR], invoice_paths=[TEST_INVOICE])

    if result:
        print("Дані успішно розпізнано:")
        print(json.dumps(result, indent=4, ensure_ascii=False))