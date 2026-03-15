import pandas as pd
import time
import sys

# Завантаження реального набору даних
file_path = 'energy_dataset.csv'

try:
    print(f"Завантаження даних з файлу {file_path}...")
    df = pd.read_csv(file_path)
except FileNotFoundError:
    print(f"\nФайл {file_path} не знайдено.")
    sys.exit()

print(f"Дані успішно завантажено. Розмір датасету: {df.shape[0]} рядків, {df.shape[1]} стовпців.")

# Для зручності візьмемо 2-й та 3-й стовпці (індекси 1 та 2)
col_type = df.columns[1]
col_value = df.columns[2]

print(f"\nДля аналізу обрано два стовпці:")
print(f"1. Категорія: '{col_type}'")
print(f"2. Значення: '{col_value}'")

# Залишаємо лише потрібні стовпці та видаляємо порожні значення
df = df[[col_type, col_value]].dropna()

# Знаходимо унікальні типи будівель (наприклад, Residential, Commercial, Industrial)
categories = df[col_type].unique()
if len(categories) < 3:
    print("\nУ датасеті знайдено менше 3 категорій будівель.")
    sys.exit()

cat1, cat2, cat3 = categories[:3]
print(f"\nАналізуємо категорії: '{cat1}', '{cat2}', '{cat3}'")

# Розрахунок медіани для кожного типу будівлі
med1 = df[df[col_type] == cat1][col_value].median()
med2 = df[df[col_type] == cat2][col_value].median()
med3 = df[df[col_type] == cat3][col_value].median()

print(f"\nМедіанні значення споживання:")
print(f"- {cat1}: {med1:.2f}")
print(f"- {cat2}: {med2:.2f}")
print(f"- {cat3}: {med3:.2f}\n")

# Традиційна фільтрація
start_time = time.time()
# Шукаємо рядки, де значення вище медіани для відповідної категорії
filtered_standard = df[
    ((df[col_type] == cat1) & (df[col_value] > med1)) |
    ((df[col_type] == cat2) & (df[col_value] > med2)) |
    ((df[col_type] == cat3) & (df[col_value] > med3))
]
standard_time = time.time() - start_time

# Фільтрація за допомогою query()
start_time = time.time()
# Зворотні апострофи ` ` використовуються для назв стовпців на випадок пробілів
query_string = (
    f"(`{col_type}` == @cat1 and `{col_value}` > @med1) or "
    f"(`{col_type}` == @cat2 and `{col_value}` > @med2) or "
    f"(`{col_type}` == @cat3 and `{col_value}` > @med3)"
)
filtered_query = df.query(query_string)
query_time = time.time() - start_time

# Оцінка продуктивності та результатів
print("Результати продуктивності")
print(f"Час традиційної фільтрації:  {standard_time:.5f} секунд")
print(f"Час фільтрації через query(): {query_time:.5f} секунд")

are_equal = filtered_standard.equals(filtered_query)
print(f"\nЧи збігаються результати обох методів? {'Так' if are_equal else 'Ні'}")
print(f"Кількість знайдених рядків (споживання вище медіани для свого типу): {len(filtered_query)}")