import pandas as pd
import numpy as np

# Створення тестового набору даних
data = {
    'product': ['A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'C', 'C', 'C', 'C'],
    'rating': [4.0, 5.0, 0.5, 9.0, 3.0, 3.5, -2.0, 3.2, 5.0, 6.5, 4.0, 4.5]
}
df = pd.DataFrame(data)

print("Початкові дані")
print(df)

# Розрахунок середнього рейтингу перед будь-якими маніпуляціями
mean_before = df.groupby('product')['rating'].mean().rename('mean_before')

# Виявлення некоректних значень та заміна їх на NaN
# Зберігаємо результат у нову колонку
df['rating_cleaned'] = df['rating'].where((df['rating'] >= 1) & (df['rating'] <= 5), np.nan)

print("\nДані після заміни некоректних значень на NaN")
print(df[['product', 'rating', 'rating_cleaned']])

# Виконання імпутації медіаною по кожному продукту
df['rating_imputed'] = df.groupby('product')['rating_cleaned'].transform(
    lambda x: x.fillna(x.median())
)

print("\nДані після імпутації медіаною по продукту")
print(df[['product', 'rating', 'rating_cleaned', 'rating_imputed']])

# Розрахунок середнього рейтингу після імпутації
mean_after = df.groupby('product')['rating_imputed'].mean().rename('mean_after')

# Порівняння середнього рейтингу товарів до і після
comparison = pd.concat([mean_before, mean_after], axis=1)
comparison['difference'] = comparison['mean_after'] - comparison['mean_before']

print("\nПорівняння середнього рейтингу товарів")
print(comparison)