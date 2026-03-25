import re

from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import torch
import os


from pathlib import Path

class FraudDetector:
    def __init__(self, model_path="model/distilbert_model"):
        model_path = Path(__file__).resolve().parent / model_path
        tokenizer_path = model_path  # если файлы модели и токенизатора в одной папке

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DistilBertForSequenceClassification.from_pretrained(str(model_path)).to(self.device)
        self.tokenizer = DistilBertTokenizer.from_pretrained(str(tokenizer_path))

    def classify_message(self, text, threshold=0.3):
        print(f"\n📨 Проверка сообщения: \"{text}\"")

        # Rule-based проверка
        if self.is_fraud_by_rules(text):
            print("⚠️ Обнаружено как мошенничество по правилам!")
            return "Мошенничество (по правилам)", 1.0

        # Классификация с помощью модели
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        inputs = {key: val.to(self.device) for key, val in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1).squeeze().tolist()

        print(f"➡️ Вероятности: не мошенничество = {probabilities[0]:.2f}, мошенничество = {probabilities[1]:.2f}")

        if probabilities[1] >= threshold:
            print("🔴 Мошенничество (по модели)")
            return "Мошенничество", probabilities[1]
        else:
            print("🟢 Не мошенничество")
            return "Не мошенничество", probabilities[0]

    import re

    def is_fraud_by_rules(self, text):
        fraud_keywords = ["скинь", "переведи", "карта"]
        context_words = ["куплю", "обед", "поесть", "завтрак", "проезд", "еда"]

        contains_fraud_keywords = any(word in text for word in fraud_keywords)
        contains_digits = any(char.isdigit() for char in text)
        contains_context_words = any(word in text for word in context_words)

        # Проверка на 16-значный номер карты
        card_pattern = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
        contains_card_number = bool(card_pattern.search(text))

        # Извлекаем числа из текста
        numbers = [int(s) for s in text.split() if s.isdigit()]
        max_amount = max(numbers) if numbers else 0

        # Если есть номер карты — это 100% мошенничество
        if contains_card_number:
            return True

        # Если есть мошеннические слова + цифры, но также есть контекст бытовых расходов — не мошенничество
        if contains_fraud_keywords and contains_digits:
            if contains_context_words and max_amount < 1000:
                return False
            return True

        return False

