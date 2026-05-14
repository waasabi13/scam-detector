import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report
)
from sklearn.utils.class_weight import compute_class_weight

from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup
)


# =========================
# Настройки
# =========================

SEED = 42
MODEL_NAME = "distilbert-base-multilingual-cased"
MAX_LEN = 128
BATCH_SIZE = 16
EPOCHS = 10
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 1e-4

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR.parent / "dataset" / "fraud_dataset.csv"
SAVE_PATH = BASE_DIR.parent / "backend" / "detector" / "model" / "distilbert_model"


# =========================
# Фиксация случайности
# =========================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# =========================
# Аугментация текста
# =========================

def augment_text(text: str) -> str:
    replacements = {
        "срочно": ["немедленно", "как можно быстрее", "прямо сейчас"],
        "перейди по ссылке": ["открой ссылку", "кликни сюда", "нажми на ссылку"],
        "получи бонус": ["забери приз", "получи подарок", "акция для вас"],
        "выиграл приз": ["тебе повезло", "ты стал победителем", "твой подарок готов"],
        "переведи деньги": ["скинь деньги", "отправь средства", "перекинь сумму"],
        "подтверди данные": ["верифицируй данные", "подтверди информацию", "обнови данные"],
        "введите код": ["укажите код", "сообщите код", "подтвердите кодом"],
        "карта заблокирована": ["счет ограничен", "доступ к карте ограничен", "карта временно недоступна"],
    }

    new_text = text.lower()

    for key, variants in replacements.items():
        if key in new_text:
            new_text = new_text.replace(key, random.choice(variants))

    return new_text


# =========================
# Dataset
# =========================

class FraudDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# =========================
# Загрузка и подготовка данных
# =========================

df = pd.read_csv(DATASET_PATH)

required_columns = {"text", "label"}
if not required_columns.issubset(df.columns):
    raise ValueError("CSV-файл должен содержать колонки 'text' и 'label'.")

df = df.dropna(subset=["text", "label"])
df["text"] = df["text"].astype(str)
df["label"] = df["label"].astype(int)

df = df[df["label"].isin([0, 1])]

print("=== Исходный датасет ===")
print(f"Всего сообщений: {len(df)}")
print(df["label"].value_counts().rename(index={0: "Не мошенничество", 1: "Мошенничество"}))
print()


# =========================
# Балансировка классов
# =========================

normal_df = df[df["label"] == 0]
fraud_df = df[df["label"] == 1]

if len(normal_df) > len(fraud_df):
    fraud_df = fraud_df.sample(n=len(normal_df), replace=True, random_state=SEED)
elif len(fraud_df) > len(normal_df):
    normal_df = normal_df.sample(n=len(fraud_df), replace=True, random_state=SEED)

df = pd.concat([normal_df, fraud_df])
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

print("=== После балансировки ===")
print(f"Всего сообщений: {len(df)}")
print(df["label"].value_counts().rename(index={0: "Не мошенничество", 1: "Мошенничество"}))
print()


# =========================
# Аугментация мошеннических сообщений
# =========================

augmented_rows = []

for _, row in df.iterrows():
    augmented_rows.append({
        "text": row["text"],
        "label": int(row["label"])
    })

    if row["label"] == 1 and random.random() > 0.4:
        augmented_rows.append({
            "text": augment_text(row["text"]),
            "label": int(row["label"])
        })

df = pd.DataFrame(augmented_rows)
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

print("=== После аугментации ===")
print(f"Всего сообщений: {len(df)}")
print(df["label"].value_counts().rename(index={0: "Не мошенничество", 1: "Мошенничество"}))
print()


# =========================
# Разделение на train/test
# =========================

train_texts, test_texts, train_labels, test_labels = train_test_split(
    df["text"],
    df["label"],
    test_size=0.2,
    stratify=df["label"],
    random_state=SEED
)

print("=== Разделение выборки ===")
print(f"Train: {len(train_texts)}")
print(f"Test:  {len(test_texts)}")
print()


# =========================
# Модель и токенизатор
# =========================

tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)
model = DistilBertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2
)

model.to(device)

train_dataset = FraudDataset(train_texts, train_labels, tokenizer, MAX_LEN)
test_dataset = FraudDataset(test_texts, test_labels, tokenizer, MAX_LEN)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)


# =========================
# Loss, optimizer, scheduler
# =========================

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.array([0, 1]),
    y=df["label"]
)

class_weights = torch.tensor(class_weights, dtype=torch.float).to(device)
loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)

optimizer = AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)

total_steps = len(train_loader) * EPOCHS

scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=0,
    num_training_steps=total_steps
)


print("=== Параметры обучения ===")
print(f"Модель: {MODEL_NAME}")
print(f"Device: {device}")
print(f"Epochs: {EPOCHS}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Learning rate: {LEARNING_RATE}")
print(f"Max sequence length: {MAX_LEN}")
print(f"Total training steps: {total_steps}")
print()


# =========================
# Обучение
# =========================

train_losses = []

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

    for batch in train_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        loss = loss_fn(outputs.logits, labels)

        loss.backward()
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(train_loader)
    train_losses.append(avg_loss)

    print(f"Epoch {epoch + 1}/{EPOCHS} | Training Loss: {avg_loss:.4f}")


# =========================
# Оценка модели
# =========================

model.eval()

predictions = []
true_labels = []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs.logits
        preds = torch.argmax(logits, dim=1)

        predictions.extend(preds.cpu().numpy())
        true_labels.extend(labels.cpu().numpy())


accuracy = accuracy_score(true_labels, predictions)
precision = precision_score(true_labels, predictions, zero_division=0)
recall = recall_score(true_labels, predictions, zero_division=0)
f1 = f1_score(true_labels, predictions, zero_division=0)

cm = confusion_matrix(true_labels, predictions)

print()
print("=== Результаты оценки модели ===")
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"F1-score:  {f1:.4f}")

print()
print("=== Матрица ошибок ===")
print("Строки — реальные классы, столбцы — предсказанные классы")
print("Классы: 0 — не мошенничество, 1 — мошенничество")
print(cm)

print()
print("=== Classification Report ===")
print(classification_report(
    true_labels,
    predictions,
    target_names=["Не мошенничество", "Мошенничество"],
    zero_division=0
))


# =========================
# Сохранение модели
# =========================

SAVE_PATH.mkdir(parents=True, exist_ok=True)

model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)

print()
print(f"Модель и токенизатор сохранены в: {SAVE_PATH}")