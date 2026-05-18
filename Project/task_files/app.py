import streamlit as st
import os
import json
from PIL import Image

# Імпортуємо наші модулі
from parser import parse_rmpd_html
from ocr_by_api import extract_data_from_documents
from validator import validate_documents
from sent_checker import check_hs_codes_against_sent

# Налаштування сторінки
st.set_page_config(page_title="RMPD AI Checker", page_icon="", layout="wide")

# Заголовок
st.title("Перевірка декларацій RMPD з AI")
st.markdown("Завантажте файли для автоматичної перевірки даних, дозволів та товарних кодів SENT.")

# Створюємо тимчасову папку для збереження завантажених файлів
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Створюємо колонки для завантаження
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Декларація RMPD")
    rmpd_file = st.file_uploader("Декларація (HTML)", type=['html'])

with col2:
    st.subheader("2. Документи CMR")
    cmr_files = st.file_uploader("Фото CMR (до 5 шт.)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

with col3:
    st.subheader("3. Інвойси (Опціонально)")
    invoice_files = st.file_uploader("Фото Інвойсу (до 5 шт.)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)


# Завантаження БД з JSON
def load_db(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"Помилка читання бази {filename}: {e}")
            return {}
    else:
        st.sidebar.warning(f"WARNING: Файл бази {filename} не знайдено.")
        return {}


# Завантажуємо бази на старті
ecmt_db = load_db("ecmt_database.json")
gps_db = load_db("gps_database.json")

# Показуємо статус баз у бічній панелі
st.sidebar.header("Статус баз даних")
st.sidebar.write(f"База GPS: **{len(gps_db)} записів**")
st.sidebar.write(f"База ЄКМТ: **{len(ecmt_db)} записів**")

# Кнопка запуску
if st.button("Запустити перевірку з AI", type="primary", use_container_width=True):
    if not rmpd_file or not cmr_files:
        st.error("Будь ласка, завантажте щонайменше декларацію RMPD та хоча б одне фото CMR.")
    elif len(cmr_files) > 5 or (invoice_files and len(invoice_files) > 5):
        st.error("ERROR: Перевищено ліміт файлів! Завантажте не більше 5 CMR та 5 Інвойсів.")
    else:
        with st.spinner("Перевірка виконується... Це може зайняти 15-20 секунд."):
            # Зберігаємо RMPD
            rmpd_path = os.path.join(TEMP_DIR, rmpd_file.name)
            with open(rmpd_path, "wb") as f:
                f.write(rmpd_file.getbuffer())

            # Зберігаємо всі CMR файли
            cmr_paths = []
            for f in cmr_files:
                path = os.path.join(TEMP_DIR, f.name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
                cmr_paths.append(path)

            # Зберігаємо всі файли Інвойсів
            invoice_paths = []
            if invoice_files:
                for f in invoice_files:
                    path = os.path.join(TEMP_DIR, f.name)
                    with open(path, "wb") as out:
                        out.write(f.getbuffer())
                    invoice_paths.append(path)

            # Парсинг RMPD
            rmpd_data = parse_rmpd_html(rmpd_path)

            # OCR Документів
            ocr_data = extract_data_from_documents(cmr_paths=cmr_paths, invoice_paths=invoice_paths)

            if rmpd_data and ocr_data:
                # Валідація (передаємо завантажені словники)
                report = validate_documents(rmpd_data, ocr_data, ecmt_db=ecmt_db, gps_db=gps_db)

                # Перевірка SENT
                hs_codes = ocr_data.get('hs_codes', [])
                sent_report = check_hs_codes_against_sent(hs_codes)

                # Візуалізація
                st.success("OK: Перевірку успішно завершено!")

                tab1, tab2, tab3 = st.tabs(["Звіт про розбіжності", "Звіт перевірки кодів (SENT)", "Розпізнані дані (JSON)"])

                with tab1:
                    st.subheader("Порівняння декларації та документів")
                    for item in report:
                        status_str = str(item.get('status', ''))

                        is_success = "OK:" in status_str or "Збіг" in status_str or "Логічно" in status_str
                        is_warning = "WARNING:" in status_str or "Попередження" in status_str

                        text_out = f"**{item['label']}** | Схожість: {item['similarity']}%\n\n**RMPD:** {item['rmpd_value']} ➡ **Оригінал/База:** {item['ocr_value']}"

                        if is_success:
                            st.success(text_out)
                        elif is_warning:
                            st.warning(text_out)  # <--- Жовтий колір для 80-99%
                        else:
                            st.error(text_out)

                with tab2:
                    st.subheader("Перевірка товарних кодів SENT")
                    st.write(f"Знайдені коди в документах: {', '.join(hs_codes) if hs_codes else 'Немає'}")
                    if sent_report['flagged']:
                        st.error(sent_report['status'])
                        for flagged in sent_report['flagged']:
                            st.warning(f"Код: **{flagged['invoice_code']}** - {flagged['reason']}")
                    else:
                        st.success(sent_report['status'])

                with tab3:
                    col_json1, col_json2 = st.columns(2)
                    with col_json1:
                        st.write("Дані з RMPD:")
                        st.json(rmpd_data)
                    with col_json2:
                        st.write("Дані з OCR (Gemini):")
                        st.json(ocr_data)

            else:
                st.error("Виникла помилка при розпізнаванні файлів. Перевірте консоль для деталей.")