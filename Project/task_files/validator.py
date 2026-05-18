import difflib
from google import genai

API_KEY = ""

def clean_text(text):
    # Видаляє всі види лапок для коректного порівняння та переводить у верхній регістр
    if not text:
        return ""
    cleaned = str(text).replace('"', '').replace("'", "").replace("«", "").replace("»", "").replace("„", "").replace(
        "”", "")
    return cleaned.strip().upper()


def calculate_similarity(str1, str2):
    # Обчислює відсоток схожості між двома рядками
    if not str1 and not str2:
        return 100.0
    if not str1 or not str2:
        return 0.0

    s1 = clean_text(str1)
    s2 = clean_text(str2)

    matcher = difflib.SequenceMatcher(None, s1, s2)
    return round(matcher.ratio() * 100, 2)


def clean_vehicle_number(v_num):
    # Видаляє всі пробіли та дефіси з номерних знаків для строгого порівняння
    if not v_num:
        return ""
    return str(v_num).replace(" ", "").replace("-", "").strip().upper()


def get_nested_value(data, key_path):
    # Дістає значення зі вкладених словників
    keys = key_path.split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, "")
        else:
            return ""
    return val


def check_transit_logic(load_country, unload_country, entrance, exit_point):
    # Запитує в AI, чи географічно логічний транзитний маршрут
    prompt = f"""
    Ти експерт з географії та європейської логістики.
    Вантажівка їде з країни '{load_country}' до країни '{unload_country}'.
    Маршрут проходить транзитом через Польщу.
    В'їзд у Польщу здійснюється через: {entrance}.
    Виїзд з Польщі здійснюється через: {exit_point}.

    Чи є цей транзитний маршрут логічним і географічно доцільним?
    Відповідай у форматі: "ТАК: [коротке пояснення]" або "НІ: [коротке пояснення чому це нелогічно]".
    """
    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text.strip()
        is_logical = text.upper().startswith("ТАК") or text.upper().startswith("YES")
        return is_logical, text
    except Exception as e:
        return False, f"Помилка перевірки AI: {e}"


def check_legal_basis_logic(legal_basis, load_country, unload_country):
    # Запитує в AI, чи коректна правова підстава для звільнення від дозволу
    prompt = f"""
    Ти експерт з європейського митного та транспортного права.
    Вантажівка здійснює міжнародне перевезення з країни '{load_country}' до країни '{unload_country}'.
    Для звільнення від дозволу на перевезення заявлена наступна правова підстава (Legal Basis):
    "{legal_basis}"

    Чи є ця угода/підстава юридично коректною, актуальною та релевантною для такого маршруту?
    Відповідай у форматі: "ТАК: [коротке пояснення]" або "НІ: [коротке пояснення чому це некоректно]".
    """
    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text.strip()
        is_logical = text.upper().startswith("ТАК") or text.upper().startswith("YES")
        return is_logical, text
    except Exception as e:
        return False, f"Помилка перевірки AI: {e}"


def validate_documents(rmpd_data, ocr_data, ecmt_db=None, gps_db=None):
    # Порівнює дані з RMPD та OCR, перевіряє GPS, ЄКМТ та географію маршруту
    report = []

    # Порівняння полів
    fields_to_compare = [
        {"key_rmpd": "sender_name", "key_ocr": "sender_name", "label": "Відправник (Назва)", "type": "text"},
        {"key_rmpd": "sender_address.street", "key_ocr": "sender_address.street", "label": "Відправник (Вулиця)",
         "type": "text"},
        {"key_rmpd": "sender_address.postal_code", "key_ocr": "sender_address.postal_code",
         "label": "Відправник (Індекс)", "type": "text"},
        {"key_rmpd": "sender_address.city", "key_ocr": "sender_address.city", "label": "Відправник (Місто)",
         "type": "text"},
        {"key_rmpd": "recipient_name", "key_ocr": "recipient_name", "label": "Одержувач (Назва)", "type": "text"},
        {"key_rmpd": "recipient_address.street", "key_ocr": "recipient_address.street", "label": "Одержувач (Вулиця)",
         "type": "text"},
        {"key_rmpd": "recipient_address.postal_code", "key_ocr": "recipient_address.postal_code",
         "label": "Одержувач (Індекс)", "type": "text"},
        {"key_rmpd": "recipient_address.city", "key_ocr": "recipient_address.city", "label": "Одержувач (Місто)",
         "type": "text"},
        {"key_rmpd": "carrier_name", "key_ocr": "carrier_name", "label": "Перевізник (Назва)", "type": "text"},
        {"key_rmpd": "carrier_address.street", "key_ocr": "carrier_address.street", "label": "Перевізник (Вулиця)",
         "type": "text"},
        {"key_rmpd": "carrier_address.postal_code", "key_ocr": "carrier_address.postal_code",
         "label": "Перевізник (Індекс)", "type": "text"},
        {"key_rmpd": "carrier_address.city", "key_ocr": "carrier_address.city", "label": "Перевізник (Місто)",
         "type": "text"},
        {"key_rmpd": "truck_number", "key_ocr": "truck_number", "label": "Номер тягача", "type": "vehicle"},
        {"key_rmpd": "trailer_number", "key_ocr": "trailer_number", "label": "Номер причепа", "type": "vehicle"},
        {"key_rmpd": "load_country", "key_ocr": "load_country", "label": "Країна завантаження", "type": "text"},
        {"key_rmpd": "unload_country", "key_ocr": "unload_country", "label": "Країна розвантаження", "type": "text"},
        {"key_rmpd": "transport_doc_number", "key_ocr": "cmr_number", "label": "Номер CMR", "type": "text"}
    ]

    for field in fields_to_compare:
        val_rmpd = get_nested_value(rmpd_data, field["key_rmpd"])
        val_ocr = get_nested_value(ocr_data, field["key_ocr"])

        if field["type"] == "vehicle":
            similarity = calculate_similarity(clean_vehicle_number(val_rmpd), clean_vehicle_number(val_ocr))
        else:
            similarity = calculate_similarity(val_rmpd, val_ocr)

        if similarity == 100.0:
            status = "OK: Збіг"
        elif similarity >= 80.0:
            status = "WARNING: Попередження (можлива опечатка OCR)"
        else:
            status = "ERROR: Помилка"

        report.append({
            "label": field["label"],
            "rmpd_value": val_rmpd if val_rmpd else "Немає даних",
            "ocr_value": val_ocr if val_ocr else "Немає даних",
            "similarity": similarity,
            "status": status
        })

    # Географічна та маршрутна перевірка
    road_type = rmpd_data.get("road_transport_type", "")
    load_country = rmpd_data.get("load_country", "")
    unload_country = rmpd_data.get("unload_country", "")
    entrance = rmpd_data.get("place_of_entrance_to_poland", "")
    exit_point = rmpd_data.get("place_of_exit_from_poland", "")
    start_inside = rmpd_data.get("place_of_start_inside_poland", "")
    end_inside = rmpd_data.get("place_of_end_inside_poland", "")

    if ("Transit" in str(road_type) or "Транзит" in str(road_type)) and entrance and exit_point:
        is_logical, expl = check_transit_logic(load_country, unload_country, entrance, exit_point)
        report.append({
            "label": "AI Маршрут (Транзит)",
            "rmpd_value": f"{entrance} -> {exit_point}",
            "ocr_value": expl if expl else "Перевірка не вдалася",
            "similarity": 100.0 if is_logical else 0.0,
            "status": "OK: Логічно" if is_logical else "ERROR: Підозріло"
        })

    if start_inside:
        load_street = get_nested_value(ocr_data, "load_address.street")
        load_city = get_nested_value(ocr_data, "load_address.city")
        ocr_load_full = f"{load_street} {load_city}".strip()

        sim = calculate_similarity(start_inside, ocr_load_full)
        if sim >= 80.0:
            status = "OK: Збіг"
        elif sim >= 50.0:
            status = "WARNING: Попередження (перевірте адресу)"
        else:
            status = "ERROR: Помилка"

        report.append({
            "label": "Місце старту (Польща)",
            "rmpd_value": start_inside,
            "ocr_value": ocr_load_full if ocr_load_full else "Немає в Полі 4 CMR",
            "similarity": sim,
            "status": status
        })

    if end_inside:
        unload_street = get_nested_value(ocr_data, "unload_address.street")
        unload_city = get_nested_value(ocr_data, "unload_address.city")
        ocr_unload_full = f"{unload_street} {unload_city}".strip()

        sim = calculate_similarity(end_inside, ocr_unload_full)
        if sim >= 80.0:
            status = "OK: Збіг"
        elif sim >= 50.0:
            status = "WARNING: Попередження (перевірте адресу)"
        else:
            status = "ERROR: Помилка"

        report.append({
            "label": "Місце фінішу (Польща)",
            "rmpd_value": end_inside,
            "ocr_value": ocr_unload_full if ocr_unload_full else "Немає в Полі 3 CMR",
            "similarity": sim,
            "status": status
        })

    # Перевірка дозволів та правової бази
    permission_type = rmpd_data.get("permission_type", "")

    if permission_type == "EKMT permit":
        ecmt_number = rmpd_data.get("permission_number", "")
        rmpd_valid_from = rmpd_data.get("valid_from", "")
        rmpd_valid_to = rmpd_data.get("valid_to", "")

        if ecmt_db and ecmt_number in ecmt_db:
            db_valid_from = ecmt_db[ecmt_number].get("valid_from", "")
            db_valid_to = ecmt_db[ecmt_number].get("valid_to", "")

            report.append({
                "label": "Дозвіл ЄКМТ (Наявність)",
                "rmpd_value": f"№ {ecmt_number}",
                "ocr_value": "Знайдено в базі",
                "similarity": 100.0,
                "status": "OK: Збіг"
            })

            sim_from = calculate_similarity(rmpd_valid_from, db_valid_from)
            report.append({
                "label": "ЄКМТ (Дійсний з)",
                "rmpd_value": rmpd_valid_from if rmpd_valid_from else "Не вказано",
                "ocr_value": db_valid_from if db_valid_from else "Немає в базі",
                "similarity": sim_from,
                "status": "OK: Збіг" if sim_from == 100.0 else "ERROR: Помилка"
            })

            sim_to = calculate_similarity(rmpd_valid_to, db_valid_to)
            report.append({
                "label": "ЄКМТ (Дійсний до)",
                "rmpd_value": rmpd_valid_to if rmpd_valid_to else "Не вказано",
                "ocr_value": db_valid_to if db_valid_to else "Немає в базі",
                "similarity": sim_to,
                "status": "OK: Збіг" if sim_to == 100.0 else "ERROR: Помилка"
            })
        else:
            report.append({
                "label": "Дозвіл ЄКМТ (База)",
                "rmpd_value": f"№ {ecmt_number}",
                "ocr_value": "Відсутній у зовнішній базі",
                "similarity": 0.0,
                "status": "ERROR: Помилка (Не знайдено)"
            })

    elif permission_type == "Exemption from the obligation to have a permit":
        legal_basis = rmpd_data.get("legal_basis", "")
        if legal_basis:
            is_valid, expl = check_legal_basis_logic(legal_basis, load_country, unload_country)
            report.append({
                "label": "AI Правова підстава",
                "rmpd_value": legal_basis,
                "ocr_value": expl if expl else "Перевірка не вдалася",
                "similarity": 100.0 if is_valid else 0.0,
                "status": "OK: Логічно" if is_valid else "ERROR: Підозріло"
            })
        else:
            report.append({
                "label": "Правова підстава (Звільнення)",
                "rmpd_value": "Відсутня",
                "ocr_value": "Помилка: не вказано",
                "similarity": 0.0,
                "status": "ERROR: Помилка"
            })

    # Перевірка GPS локаторів
    if gps_db is not None:
        truck_number = clean_vehicle_number(rmpd_data.get("truck_number", ""))
        locator_number = rmpd_data.get("locator_number", "")
        expected_locator = gps_db.get(truck_number)

        if expected_locator and expected_locator == locator_number:
            report.append({
                "label": "GPS Локатор (База)",
                "rmpd_value": locator_number,
                "ocr_value": expected_locator,
                "similarity": 100.0,
                "status": "OK: Збіг"
            })
        else:
            report.append({
                "label": "GPS Локатор (База)",
                "rmpd_value": locator_number if locator_number else "Немає",
                "ocr_value": expected_locator if expected_locator else "Авто не знайдено в базі",
                "similarity": 0.0,
                "status": "ERROR: Помилка (Невідповідність)"
            })

    return report

def print_validation_report(report):
    # Звіт
    print(" Звіт валідації ")

    for item in report:
        print(f"Поле: {item['label']}")
        print(f"  RMPD: {item['rmpd_value']}")

        if "База" in item['label'] or "Правова" in item['label'] and not item['label'].startswith("AI"):
            print(f"  БАЗА: {item['ocr_value']}")
        elif item['label'].startswith("AI"):
            print(f"  ВЕРДИКТ АГЕНТА: {item['ocr_value']}")
        else:
            print(f"  OCR:  {item['ocr_value']}")

        if item['status'].startswith("ERROR:"):
            print(f"  Результат: {item['status']} (Схожість: {item['similarity']}%) <--- ЗВЕРНІТЬ УВАГУ")
        else:
            print(f"  Результат: {item['status']} (Схожість: {item['similarity']}%)")