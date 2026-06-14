import re
from pathlib import Path

import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification


class FraudDetector:
    def __init__(self, model_path="model/distilbert_model"):
        model_path = Path(__file__).resolve().parent / model_path

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DistilBertForSequenceClassification.from_pretrained(str(model_path)).to(self.device)
        self.tokenizer = DistilBertTokenizer.from_pretrained(str(model_path))

    def classify_message(self, text, threshold=0.75):
        text = self.normalize_text(text)

        simple_safe = [
            "привет",
            "как дела",
            "привет как дела",
            "доброе утро",
            "добрый вечер",
            "спасибо",
            "пока",
            "что делаешь",
            "как настроение"
        ]

        if text in simple_safe:
            return "Не мошенничество", 1.0

        if self.is_fraud_by_rules(text):
            return "Мошенничество (по правилам)", 1.0

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        inputs = {key: val.to(self.device) for key, val in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        probabilities = torch.softmax(outputs.logits, dim=1).squeeze().tolist()

        normal_probability = probabilities[0]
        fraud_probability = probabilities[1]

        if fraud_probability >= threshold:
            return "Мошенничество", fraud_probability

        return "Не мошенничество", normal_probability

    def normalize_text(self, text):
        text = str(text).lower().strip()
        text = text.replace("ё", "е")
        text = re.sub(r"\s+", " ", text)
        return text

    def is_fraud_by_rules(self, text):
        text = self.normalize_text(text)

        link_pattern = re.compile(
            r"(https?://|www\.|t\.me/|bit\.ly|clck\.ru|goo\.su|tinyurl|vk\.cc)"
        )
        card_pattern = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

        contains_link = bool(link_pattern.search(text))
        contains_card_number = bool(card_pattern.search(text))

        code_words = [
            "код", "смс", "sms", "пароль", "otp", "подтверждение",
            "push", "пуш", "одноразовый", "секретный код"
        ]

        code_request_words = [
            "сообщи", "пришли", "отправь", "напиши",
            "назови", "введи", "продиктуй"
        ]

        pressure_words = [
            "срочно", "немедленно", "последний шанс", "сейчас же",
            "иначе", "будут проблемы", "последствия", "заблокируют",
            "заблокирована", "ограничат", "оштрафуют", "полиция",
            "суд", "уголовное дело", "служба безопасности",
            "не откладывай", "в течение часа", "до вечера"
        ]

        money_action_words = [
            "переведи", "переведите", "отправь", "отправьте",
            "скинь", "скиньте", "перекинь", "перекиньте",
            "оплати", "оплатите", "заплати", "заплатите",
            "кинь", "киньте"
        ]

        suspicious_money_words = [
            "штраф", "комиссия", "налог", "задолженность",
            "верификация", "активация", "разблокировка",
            "выплата", "компенсация", "выигрыш", "приз",
            "бонус", "страховой платеж", "подтверждение платежа"
        ]

        bank_words = [
            "банк", "карта", "счет", "аккаунт", "личный кабинет",
            "госуслуги", "служба безопасности", "оператор банка"
        ]

        threat_words = [
            "найду", "приеду", "родственникам", "на работу",
            "выложу", "распространю", "опубликую", "пожалеешь",
            "будет хуже", "не заставляй", "последнее предупреждение"
        ]

        safe_context_words = [
            "такси", "обед", "ужин", "завтрак", "еда", "поесть", "покушать",
            "кофе", "продукты", "магазин", "проезд", "автобус", "метро",
            "бензин", "доставка", "пицца", "подарок", "цветы",
            "кроссовки", "обувь", "куртка", "одежда", "футболка",
            "лекарства", "аптека", "тетради", "учебники", "школа",
            "универ", "учеба", "оплата заказа", "заказ", "билет",
            "кино", "кафе", "не хватает", "верну завтра",
            "верну вечером", "верну после зарплаты"
        ]

        trusted_relation_words = [
            "мам", "мама", "пап", "папа", "брат", "сестра",
            "друг", "подруга", "сын", "дочь", "родной",
            "пожалуйста", "плиз", "можешь", "можно",
            "одолжи", "одолжишь", "занять"
        ]

        contains_code_words = any(word in text for word in code_words)
        contains_code_request = any(word in text for word in code_request_words)
        contains_pressure = any(word in text for word in pressure_words)
        contains_money_action = any(word in text for word in money_action_words)
        contains_suspicious_money = any(word in text for word in suspicious_money_words)
        contains_bank_words = any(word in text for word in bank_words)
        contains_threat = any(word in text for word in threat_words)
        contains_safe_context = any(word in text for word in safe_context_words)
        contains_trusted_relation = any(word in text for word in trusted_relation_words)

        numbers = [int(x) for x in re.findall(r"\b\d+\b", text)]
        has_amount = len(numbers) > 0

        danger_signals = (
            contains_link
            or contains_code_words
            or contains_card_number
            or contains_pressure
            or contains_threat
        )

        # -------------------------
        # Явно мошеннические признаки
        # -------------------------

        if contains_card_number:
            return True

        if contains_code_words and contains_code_request:
            return True

        if contains_link and (
            contains_money_action
            or contains_suspicious_money
            or contains_pressure
            or contains_bank_words
        ):
            return True

        if contains_pressure and (contains_money_action or contains_suspicious_money or contains_bank_words):
            return True

        if contains_threat and (contains_money_action or has_amount):
            return True

        if contains_bank_words and contains_code_words:
            return True

        if contains_suspicious_money and contains_money_action and not contains_safe_context:
            return True

        # -------------------------
        # Безопасные бытовые сценарии
        # -------------------------

        if contains_money_action and contains_safe_context and not danger_signals:
            return False

        if contains_money_action and contains_trusted_relation and not danger_signals:
            return False

        if "не хватает" in text and not danger_signals:
            return False

        if has_amount and contains_safe_context and contains_trusted_relation and not danger_signals:
            return False

        return False

    def classify_audio(self, text):
        return self.classify_message(text)