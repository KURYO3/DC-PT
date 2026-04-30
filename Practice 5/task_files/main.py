from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, accuracy_score

def main():
    # Завантаження даних, для швидкості роботи скрипта візьмемо 4 категорії текстів
    categories = [
        'alt.atheism',
        'soc.religion.christian',
        'comp.graphics',
        'sci.med'
    ]

    print("Завантаження тренувальних та тестових даних...")
    train_data = fetch_20newsgroups(subset='train', categories=categories, shuffle=True, random_state=42)
    test_data = fetch_20newsgroups(subset='test', categories=categories, shuffle=True, random_state=42)

    print(f"Завантажено {len(train_data.data)} тренувальних текстів.")
    print(f"Завантажено {len(test_data.data)} тестових текстів.\n")

    # Побудова моделей (Конвеєри)
    nb_model = make_pipeline(TfidfVectorizer(), MultinomialNB())
    svm_model = make_pipeline(TfidfVectorizer(), LinearSVC(random_state=42, dual="auto"))

    # 3. Навчання та оцінка Байєса
    print("--< Модель Naive Bayes >--")
    print("Навчання моделі...")
    nb_model.fit(train_data.data, train_data.target)

    print("Прогнозування...")
    nb_predictions = nb_model.predict(test_data.data)

    nb_accuracy = accuracy_score(test_data.target, nb_predictions)
    print(f"\nТочність: {nb_accuracy:.4f}\n")
    print("Детальний звіт:")
    print(classification_report(test_data.target, nb_predictions, target_names=train_data.target_names))

    # Навчання та оцінка SVM
    print("--< Модель SVM >--")
    print("Навчання моделі...")
    svm_model.fit(train_data.data, train_data.target)

    print("Прогнозування...")
    svm_predictions = svm_model.predict(test_data.data)

    svm_accuracy = accuracy_score(test_data.target, svm_predictions)
    print(f"\nТочність: {svm_accuracy:.4f}\n")
    print("Детальний звіт:")
    print(classification_report(test_data.target, svm_predictions, target_names=train_data.target_names))

    print("--< Тестування на власних даних >--")
    sample_texts = [
        "God is love and Jesus is the savior.",
        "My computer has a new GPU and renders 3D graphics very fast.",
        "The doctor prescribed antibiotics for the infection.",
    ]
    texts_categories = [
        "soc.religion.christian",
        "comp.graphics",
        "sci.med"
    ]

    print("Тексти для перевірки:")
    for i in range(len(sample_texts)):
        text = sample_texts[i]
        categories = texts_categories[i]
        print(f"{text} -- {categories}")


    print("\nПрогнози Наївного Байєса (Naive Bayes):")
    nb_preds = nb_model.predict(sample_texts)
    for text, category_id in zip(sample_texts, nb_preds):
        print(f"Текст: '{text}' \nПередбачена категорія: {train_data.target_names[category_id]}")

    print("\nПрогнози SVM моделі:")
    sample_preds = svm_model.predict(sample_texts)
    for text, category_id in zip(sample_texts, sample_preds):
        print(f"Текст: '{text}' \nПередбачена категорія: {train_data.target_names[category_id]}")


if __name__ == "__main__":
    main()