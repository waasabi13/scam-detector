import time
from backend.detector.fraud_detector import FraudDetector

# Инициализация детектора
model_path="model/distilbert_model"
fraud_detector = FraudDetector(model_path)

# Сообщение для проверки
message = "привет! скинь, пожалуйста, 500 рублей на такси"

# Замер времени
start_time = time.time()
result = fraud_detector.classify_message(message)
end_time = time.time()

# Вывод результатов
print(f"Результат классификации: {result}")
print(f"Время обработки: {end_time - start_time:.6f} секунд")
