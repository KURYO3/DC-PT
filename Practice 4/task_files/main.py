import os

# Вимикаємо системні попередження TensorFlow до його імпорту
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Прибирає повідомлення INFO та WARNING від C++ ядра TF
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Прибирає попередження про oneDNN

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv1D, MaxPooling1D, UpSampling1D

# Фіксуємо seed для відтворюваності результатів
np.random.seed(67)
tf.random.set_seed(67)

print("Завантаження та підготовка даних...")
# Завантажуємо датасет
df_raw = pd.read_csv('energy_dataset.csv')

# Перетворюємо стовпець Timestamp на формат datetime та робимо його індексом
df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'])
df_raw.set_index('Timestamp', inplace=True)
df_raw.sort_index(inplace=True)

# Обмежуємо розмір датасету першими 1500 записами для швидкості
df = pd.DataFrame({'truth': df_raw['Energy Consumption (kWh)'].iloc[:1500]})

# Нормалізація даних від 0 до 1
scaler = MinMaxScaler()
df['truth_scaled'] = scaler.fit_transform(df[['truth']])

print("Підготовка тестового набору даних...")
df['missing_scaled'] = df['truth_scaled'].copy()

# Створюємо випадкові поодинокі пропуски (5% даних)
random_missing_idx = np.random.choice(df.index, size=int(len(df) * 0.05), replace=False)
df.loc[random_missing_idx, 'missing_scaled'] = np.nan

# Створюємо блокові пропуски по 6 годин підряд кілька разів
for i in range(10, len(df) - 10, 100):
    df.iloc[i:i + 6, df.columns.get_loc('missing_scaled')] = np.nan

# Зберігаємо індекси де саме відсутні дані для фінальної оцінки
missing_mask = df['missing_scaled'].isna()

print(f"Загалом пропущено {missing_mask.sum()} точок з {len(df)}")

# Базові методи (Інтерполяція)
# Використовуємо чисто математичні методи pandas без bfill/ffill "милиць"
df['spline_scaled'] = df['missing_scaled'].interpolate(method='spline', order=3)
df['poly_scaled'] = df['missing_scaled'].interpolate(method='polynomial', order=2)

print("Формування датасету для автоенкодера...")
WINDOW_SIZE = 24  # Вікно в 1 добу (24 години)

# Створюємо вікна виключно з еталонних даних
clean_data = df['truth_scaled'].values
y_data = []
for i in range(len(clean_data) - WINDOW_SIZE):
    y_data.append(clean_data[i:i + WINDOW_SIZE])
y_data = np.array(y_data).reshape(-1, WINDOW_SIZE, 1)

# Створюємо Denoising Autoencoder:
# На вхід (X) подаємо чисті дані зі штучно доданими пропусками (маркер -1)
# -1 лежить за межами MinMaxScaler (0-1) тому мережа чітко розпізнає дірки
X_data = y_data.copy()
# Штучно зануляємо близько 15% точок випадковим чином для навчання
random_mask = np.random.rand(*X_data.shape) < 0.15
X_data[random_mask] = -1.0

# Розділення на тренувальну і тестову вибірки  80 на 20
split_idx = int(len(X_data) * 0.8)
X_train, X_test = X_data[:split_idx], X_data[split_idx:]
y_train, y_test = y_data[:split_idx], y_data[split_idx:]

print("Побудова та навчання автоенкодера...")


def build_autoencoder(window_size):
    input_window = Input(shape=(window_size, 1))

    # Енкодер
    x = Conv1D(16, 3, activation="relu", padding="same")(input_window)
    x = MaxPooling1D(2, padding="same")(x)
    x = Conv1D(8, 3, activation="relu", padding="same")(x)
    encoded = MaxPooling1D(2, padding="same")(x)

    # Декодер
    x = Conv1D(8, 3, activation="relu", padding="same")(encoded)
    x = UpSampling1D(2)(x)
    x = Conv1D(16, 3, activation="relu", padding="same")(x)
    x = UpSampling1D(2)(x)
    decoded = Conv1D(1, 3, activation="sigmoid", padding="same")(x)  # Вихід строго [0, 1]

    model = Model(input_window, decoded)
    model.compile(optimizer='adam', loss='mse')
    return model


autoencoder = build_autoencoder(WINDOW_SIZE)

# Навчання моделі
history = autoencoder.fit(
    X_train, y_train,
    epochs=150,
    batch_size=32,
    validation_split=0.1,
    verbose=0
)
print("Завершено")

# Оцінка та порівняння
# Замінюємо реальні пропуски маркером -1
nn_input = df['missing_scaled'].fillna(-1).values

# Щоб уникнути змішування методів і не втратити хвіст графіка,
# доповнимо масив значенням -1 до довжини, кратної WINDOW_SIZE
pad_len = (WINDOW_SIZE - (len(nn_input) % WINDOW_SIZE)) % WINDOW_SIZE
padded_input = np.pad(nn_input, (0, pad_len), constant_values=-1)

X_full = padded_input.reshape(-1, WINDOW_SIZE, 1)
predictions_scaled = autoencoder.predict(X_full, verbose=0).flatten()

# Записуємо стільки точок скільки було в оригінальному датасеті
df['autoencoder_scaled'] = predictions_scaled[:len(df)]

# Зворотна нормалізація
for col in ['truth', 'spline', 'poly', 'autoencoder']:
    if col == 'truth': continue
    df[col] = scaler.inverse_transform(df[[f'{col}_scaled']])

# Розрахунок метрик тільки для пропущених точок
eval_df = df[missing_mask].copy()


def print_metrics(y_true, y_pred, name):
    # Очищаємо від NaN для чесної метрики якщо на краях поліном/сплайн не спрацював
    valid_idx = ~np.isnan(y_pred)
    if valid_idx.sum() == 0:
        print(f"{name} -> Неможливо розрахувати (усі значення NaN)")
        return

    mae = mean_absolute_error(y_true[valid_idx], y_pred[valid_idx])
    rmse = np.sqrt(mean_squared_error(y_true[valid_idx], y_pred[valid_idx]))
    print(f"{name} -> MAE: {mae:.3f}, RMSE: {rmse:.3f}")


print("\nРезультати на пропущених даних")
print_metrics(eval_df['truth'], eval_df['spline'], "Сплайнова інтерполяція")
print_metrics(eval_df['truth'], eval_df['poly'], "Поліноміальна інтерполяція")
print_metrics(eval_df['truth'], eval_df['autoencoder'], "Автоенкодер (Conv1D)")

# Візуалізація: вибираємо 3-денний відрізок
start_plot = 100
end_plot = 172
plot_mask = missing_mask.iloc[start_plot:end_plot]

plt.figure(figsize=(15, 6))
plt.plot(df.index[start_plot:end_plot], df['truth'].iloc[start_plot:end_plot], label='Справжні дані (Truth)',
         color='black', linewidth=2)

marker_y_pos = df['truth'].iloc[start_plot:end_plot].min() - 5
plt.plot(df.index[start_plot:end_plot], df['missing_scaled'].iloc[start_plot:end_plot] * 0 + marker_y_pos, 'rx',
         label='Пропущені точки (Mask)', markersize=5)
plt.plot(df.index[start_plot:end_plot], df['spline'].iloc[start_plot:end_plot], label='Сплайни', linestyle='--')
plt.plot(df.index[start_plot:end_plot], df['autoencoder'].iloc[start_plot:end_plot], label='Автоенкодер', linestyle='-',
         color='red', alpha=0.8)

plt.title('Відновлення часового ряду')
plt.xlabel('Час')
plt.ylabel('Споживання енергії (kWh)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()