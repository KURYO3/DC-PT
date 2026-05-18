from bs4 import BeautifulSoup
import os
import json

def parse_rmpd_html(file_path):

    # Парсить HTML файл декларації і витягує ключові дані. Повертає словник з даними (усі ключі та значення англійською)
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')

    # Словник для збереження результатів
    data = {}

    # Допоміжна функція для пошуку значень за data-phrase-id
    def get_value_by_phrase_id(phrase_id):
        # Шукає <span> з певним data-phrase-id і намагається отримати значення, яке знаходиться поруч
        span = soup.find('span', {'data-phrase-id': phrase_id})
        if not span:
            return None

        parent_p = span.find_parent('p')
        if parent_p:
            text = parent_p.get_text(separator=' ', strip=True)
            label = span.get_text(strip=True)
            value = text.replace(label, '').strip()
            if value:
                return value
        return None

    # Словник для перекладу системних кодів у зрозумілий англійський текст
    PHRASE_DICT = {
        "rmpdTypeOfRoadTransport1": "Bilateral transport",
        "rmpdTypeOfRoadTransport2": "Transit transport",
        "rmpdTypeOfRoadTransport3": "3rd country transport",
        "rmpdTypeOfRoadTransport4": "Cabotage",
        "rmpdTypeOfPermission1": "Disposable permit",
        "rmpdTypeOfPermission2": "EKMT permit",
        "rmpdTypeOfPermission3": "Cabotage",
        "rmpdTypeOfPermission4": "Exemption from the obligation to have a permit",
        "rmpdJourneyDirection1": "First journey in accordance with the permit template",
        "rmpdJourneyDirection2": "Return journey in accordance with the permit template"
    }

    def parse_address_lines(lines):
        # Розбиває масив рядків адреси на словник: вулиця, індекс, місто, країна
        address = {"street": "", "postal_code": "", "city": "", "country": ""}
        if not lines:
            return address

        address["street"] = lines[0]
        if len(lines) > 1:
            parts = lines[1].split(',')
            city_zip = parts[0].strip()
            if len(parts) > 1:
                address["country"] = parts[1].strip()

            # Відокремлення індексу від міста шукаючи пробіл після цифр
            zip_city_parts = city_zip.split(' ', 1)
            if len(zip_city_parts) == 2 and any(char.isdigit() for char in zip_city_parts[0]):
                address["postal_code"] = zip_city_parts[0].strip()
                address["city"] = zip_city_parts[1].strip()
            else:
                address["city"] = city_zip
        return address

    # Допоміжна функція для витягування всіх даних про контрагента
    def extract_trader_info(phrase_id, prefix):
        header = soup.find('p', {'data-phrase-id': phrase_id})
        if header:
            div = header.find_next_sibling('div', class_='grupInfo')
            if div:
                name_span = div.find('span', {'data-phrase-id': 'rmpdTraderName'})
                if name_span and name_span.parent:
                    data[f'{prefix}_name'] = name_span.parent.get_text(strip=True).replace(
                        name_span.get_text(strip=True), '').strip()

                id_type_span = div.find('span', {'data-phrase-id': 'rmpdTraderIdentityType'})
                if id_type_span and id_type_span.parent:
                    data[f'{prefix}_identity_type'] = id_type_span.parent.get_text(strip=True).replace(
                        id_type_span.get_text(strip=True), '').strip()

                id_num_span = div.find('span', {'data-phrase-id': 'rmpdTraderIdentityNumber'})
                if id_num_span and id_num_span.parent:
                    data[f'{prefix}_identity_number'] = id_num_span.parent.get_text(strip=True).replace(
                        id_num_span.get_text(strip=True), '').strip()

                addr_span = div.find('span', {'data-phrase-id': 'rmpdAdress'})
                if addr_span and addr_span.parent:
                    lines = []
                    nxt = addr_span.parent.find_next_sibling('p')
                    while nxt:
                        lines.append(nxt.get_text(strip=True).replace('\xa0', ' '))
                        nxt = nxt.find_next_sibling('p')
                    data[f'{prefix}_address'] = parse_address_lines(lines)
                else:
                    data[f'{prefix}_address'] = {"street": "", "postal_code": "", "city": "", "country": ""}

    # Деталі учасників
    extract_trader_info('rmpdGoodsSenderInfo', 'sender')
    extract_trader_info('rmpdGoodsRecipientInfo', 'recipient')
    extract_trader_info('rmpdGoodsCarrierInfo', 'carrier')

    # Умови та дозволи
    data['start_date'] = get_value_by_phrase_id('rmpdStartTransportDate')
    data['end_date'] = get_value_by_phrase_id('rmpdEndTransportDate')
    data['load_country'] = get_value_by_phrase_id('rmpdCountryLoadCode')
    data['unload_country'] = get_value_by_phrase_id('rmpdCountryUnloadCode')
    data['transport_doc_type'] = get_value_by_phrase_id('rmpdTypeOfTransportDocument')
    data['transport_doc_number'] = get_value_by_phrase_id('rmpdNumberOfTransportDocument')

    type_road_transport = soup.find('span', {'data-phrase-id': 'rmpdTypeOfRoadTransport'})
    if type_road_transport and type_road_transport.parent:
        val_span = type_road_transport.parent.find_all('span')[-1]
        raw_val = val_span.get('data-phrase-id')
        data['road_transport_type'] = PHRASE_DICT.get(raw_val, raw_val)

    type_permission = soup.find('span', {'data-phrase-id': 'rmpdTypeOfPermission'})
    if type_permission and type_permission.parent:
        val_span = type_permission.parent.find_all('span')[-1]
        raw_val = val_span.get('data-phrase-id')
        data['permission_type'] = PHRASE_DICT.get(raw_val, raw_val)

    journey_direction = soup.find('span', {'data-phrase-id': 'rmpdJourneyDirection'})
    if journey_direction and journey_direction.parent:
        val_span = journey_direction.parent.find_all('span')[-1]
        raw_val = val_span.get('data-phrase-id')
        data['journey_direction'] = PHRASE_DICT.get(raw_val, raw_val)

    # Деталі ECMT
    data['permission_number'] = get_value_by_phrase_id('rmpdPermissionNumber')
    data['permission_country'] = get_value_by_phrase_id('rmpdPermissionCountry')
    data['valid_from'] = get_value_by_phrase_id('rmpdValidFrom')
    data['valid_to'] = get_value_by_phrase_id('rmpdValidTo')

    # Правові деталі
    # Спочатку шукаємо англійський опис, якщо немає, то польський
    data['legal_basis'] = get_value_by_phrase_id('rmpdNotObligedLegalBaseEn') or get_value_by_phrase_id(
        'rmpdNotObligedLegalBasePl')
    data['justification'] = get_value_by_phrase_id('rmpdNotObligedLegalBaseDescriptionEn') or get_value_by_phrase_id(
        'rmpdNotObligedLegalBaseDescriptionPl')

    # Локації та транспорт
    def get_location_info(phrase_id):
        # Знаходить місце перетину кордону або адресу завантаження/вивантаження в Польщі
        header = soup.find('p', {'data-phrase-id': phrase_id})
        if not header:
            return None
        div = header.find_next_sibling('div', class_='grupInfo')
        if not div:
            return None

        # Якщо це кордон, беремо `rmpdRoutePlace`
        route_place = div.find('span', {'data-phrase-id': 'rmpdRoutePlace'})
        if route_place and route_place.parent:
            return route_place.parent.get_text(strip=True).replace(route_place.get_text(strip=True), '').strip()

        # Якщо це адреса в Польщі (без rmpdRoutePlace), беремо чисті <p> теги
        info1 = div.find('div', class_='info1')
        if info1:
            lines = []
            for p in info1.find_all('p', recursive=False):
                # Ігноруємо теги, що містять додаткову інформацію типу координат чи провінцій
                if not p.find('span', attrs={'data-phrase-id': True}):
                    text = p.get_text(strip=True).replace('\xa0', ' ')
                    if text:
                        lines.append(text)
            if lines:
                return ", ".join(lines)
        return None

    data['place_of_entrance_to_poland'] = get_location_info('rmpdEntranceToPoland')
    data['place_of_exit_from_poland'] = get_location_info('rmpdExitFromPoland')
    data['place_of_start_inside_poland'] = get_location_info('rmpdStartInsidePL')
    data['place_of_end_inside_poland'] = get_location_info('rmpdEndInsidePL')

    # Транспортні засоби
    data['truck_country'] = get_value_by_phrase_id('rmpdTruckCountry')
    data['truck_number'] = get_value_by_phrase_id('rmpdTruckNumber')
    data['trailer_country'] = get_value_by_phrase_id('rmpdTrailerCountry')
    data['trailer_number'] = get_value_by_phrase_id('rmpdTrailerNumber')
    data['locator_number'] = get_value_by_phrase_id('rmpdLocatorNumber')

    # Очищуємо порожні значення, які не знайшлися в цьому конкретному файлі, щоб JSON був чистішим
    cleaned_data = {k: v for k, v in data.items() if v is not None}

    return cleaned_data

if __name__ == "__main__":
    test_files = [
        "RMPD20250125001873 (RMPD_110).html",
        "RMPD20260326004666 (RMPD_111).xml (2).html",
        "RMPD20260330000537 (RMPD_110).xml.html"
    ]

    for file in test_files:
        print(f"\nAnalyzing file: {file}")
        parsed_data = parse_rmpd_html(file)
        if parsed_data:
            print(json.dumps(parsed_data, indent=4, ensure_ascii=False))