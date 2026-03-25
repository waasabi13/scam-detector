# scripts/test_model.py
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
from tqdm import tqdm

# Загрузка датасета
df = pd.read_csv("../dataset/fraud_dataset.csv")

# Разделение данных на обучающую и тестовую выборки
_, test_texts, _, test_labels = train_test_split(
    df["text"], df["label"], test_size=0.2, random_state=42
)

# Создание Dataset и DataLoader
class FraudDataset(torch.utils.data.Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding="max_length",
            truncation=True,
            return_attention_mask=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": torch.tensor(label, dtype=torch.long),
        }

# Загрузка модели и токенизатора
model = DistilBertForSequenceClassification.from_pretrained("../fraud_detection_module/model/distilbert_model")
tokenizer = DistilBertTokenizer.from_pretrained("../fraud_detection_module/model/tokenizer")

# Переводим модель на GPU, если доступно
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Создание DataLoader
test_dataset = FraudDataset(test_texts.tolist(), test_labels.tolist(), tokenizer)
test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

# Тестирование модели
model.eval()
predictions, true_labels = [], []

with torch.no_grad():
    for batch in tqdm(test_loader):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits
        preds = torch.argmax(logits, dim=1).cpu().numpy()

        predictions.extend(preds)
        true_labels.extend(labels.cpu().numpy())

# Оценка модели
accuracy = accuracy_score(true_labels, predictions)
print(f"Accuracy: {accuracy}")
print(classification_report(true_labels, predictions))