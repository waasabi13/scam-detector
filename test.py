import time
from backend.detector.fraud_detector import FraudDetector

# Инициализация детектора
fraud_detector = FraudDetector(model_path="backend/detector/model/distilbert_model",
                               tokenizer_path="backend/detector/model/tokenizer")

# Сообщение для проверки
message = "Срочная информация! Ваш номер участвует в розыгрыше миллиона рублей: lucky-number.ru."

# Замер времени
start_time = time.time()
result = fraud_detector.classify_message(message)
end_time = time.time()

# Вывод результатов
print(f"Результат классификации: {result}")
print(f"Время обработки: {end_time - start_time:.6f} секунд")
