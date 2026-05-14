import random

def generate_augmented_samples(text):

    replacements = {
        "переведи деньги": [
            "скинь деньги",
            "отправь средства",
            "перекинь сумму",
            "жду деньги",
            "перекинь деньги"
        ],
        "перейди по ссылке": [
            "открой ссылку",
            "кликни сюда",
            "нажми на ссылку"
        ],
        "срочно": [
            "немедленно",
            "прямо сейчас",
            "как можно быстрее"
        ],
        "подтверди": [
            "верифицируй",
            "подтверди данные",
            "подтверди информацию"
        ],
        "напишу заявление": [
            "солью данные",
            "солью переписку",
            "сдам тебя"
        ]
    }

    results = set()
    results.add(text)

    for _ in range(10):
        new_text = text

        for key, variants in replacements.items():
            if key in new_text:
                new_text = new_text.replace(key, random.choice(variants))

        results.add(new_text)

    return list(results)


if __name__ == "__main__":
    original = "Срочно переведи деньги мне на карту, или я напишу заявление!"

    augmented = generate_augmented_samples(original)

    print("Исходное сообщение:")
    print(original)
    print("\nСгенерированные варианты:\n")

    for i, text in enumerate(augmented, 1):
        print(f"{i}. {text}")