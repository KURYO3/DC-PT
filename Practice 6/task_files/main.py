import pandas as pd
import matplotlib.pyplot as plt


def analyze_magnetic_data(file_path):
    try:
        data = pd.read_csv(file_path)

        time_col = 'Time (s)'
        abs_field_col = 'Absolute field (µT)'

        if time_col in data.columns and abs_field_col in data.columns:
            mean_value = data[abs_field_col].mean()
            max_value = data[abs_field_col].max()

            print(f"Файл: {file_path}")
            print(f"Середнє значення:      {mean_value:.2f} мкТл")
            print(f"Максимальне значення:  {max_value:.2f} мкТл")

            plt.figure(figsize=(10, 5))

            plt.plot(data[time_col], data[abs_field_col],
                     label='Абсолютне магнітне поле',
                     color='#1f77b4', linewidth=2)

            plt.axhline(y=mean_value, color='red', linestyle='--',
                        label=f'Середнє: {mean_value:.2f} мкТл')

            max_time = data.loc[data[abs_field_col].idxmax(), time_col]
            plt.plot(max_time, max_value, 'ro',
                     label=f'Максимум: {max_value:.2f} мкТл')

            plt.title(f'Зміна магнітного поля з часом ({file_path})', fontsize=14, fontweight='bold')
            plt.xlabel('Час (секунди)', fontsize=12)
            plt.ylabel('Магнітне поле (мкТл)', fontsize=12)
            plt.grid(True, linestyle=':', alpha=0.7)
            plt.legend(loc='best')
            plt.tight_layout()

            output_image = file_path.replace('.csv', '_plot.png')
            plt.savefig(output_image, dpi=300)

            plt.show()

        else:
            print(f"Невідповідний формат колонок файлу {file_path}.")
            print(f"Знайдені колонки: {list(data.columns)}\n")

    except FileNotFoundError:
        print(f"Файл '{file_path}' не знайдено.\n")
    except Exception as e:
        print(f"Помилка обробки файлу {file_path}: {e}\n")


if __name__ == "__main__":
    files_to_process = [
        'Room.csv',
        'Laptop.csv',
        'Charger.csv',
        'Fridge.csv',
        'Kettle.csv'
    ]

    print(f"Обробка {len(files_to_process)} файлів...\n")

    for file_name in files_to_process:
        analyze_magnetic_data(file_name)

    print("Обробку завершено.")