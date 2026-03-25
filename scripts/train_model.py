import torch
import random
import numpy as np
import pandas as pd
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, AdamW, get_linear_schedule_with_warmup
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.utils.class_weight import compute_class_weight

# Фиксация случайности
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)


def augment_text(text):
    replacements = {
        "получи бонус": ["забери приз", "подарок ждет", "акция для вас"],
        "перейди по ссылке": ["кликни сюда", "узнай подробнее", "жми на кнопку"],
        "выиграл приз": ["тебе повезло", "твой подарок здесь", "бери свой выигрыш"]
    }
    for key, values in replacements.items():
        if key in text:
            text = text.replace(key, random.choice(values))
    return text


# Загрузка датасета
df = pd.read_csv("../dataset/fraud_dataset.csv")

# Балансировка классов (дублируем спам-сообщения)
spam_df = df[df["label"] == 1]
df = pd.concat([df, spam_df.sample(n=len(df[df["label"] == 0]), replace=True)])

df["text"] = df["text"].apply(lambda x: augment_text(x) if random.random() > 0.5 else x)


def extract_features(text):
    return {
        "has_link": int("http" in text or ".com" in text or ".ru" in text),
        "num_digits": sum(c.isdigit() for c in text),
        "text_length": len(text),
    }


df_features = df["text"].apply(lambda x: extract_features(x)).apply(pd.Series)
df = pd.concat([df, df_features], axis=1)


# Dataset класс
class SpamDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding='max_length',
            max_length=self.max_len,
            return_tensors="pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# Загрузка модели и токенизатора
tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-multilingual-cased")
model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-multilingual-cased", num_labels=2)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Разбиение данных
train_texts, test_texts, train_labels, test_labels = train_test_split(
    df["text"], df["label"], test_size=0.2, stratify=df["label"], random_state=42
)

train_dataset = SpamDataset(train_texts.tolist(), train_labels.tolist(), tokenizer)
test_dataset = SpamDataset(test_texts.tolist(), test_labels.tolist(), tokenizer)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

# Взвешивание классов
class_weights = compute_class_weight("balanced", classes=np.unique(df["label"]), y=df["label"])
class_weights = torch.tensor(class_weights, dtype=torch.float).to(device)
loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)

# Оптимизатор и scheduler
optimizer = AdamW(model.parameters(), lr=2e-5, weight_decay=1e-4)
total_steps = len(train_loader) * 5
scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)

# Обучение модели
epochs = 10
for epoch in range(epochs):
    model.train()
    total_loss = 0
    for batch in train_loader:
        input_ids, attention_mask, labels = batch["input_ids"].to(device), batch["attention_mask"].to(device), batch[
            "labels"].to(device)
        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = loss_fn(outputs.logits, labels)
        loss.backward()
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
    print(f"Epoch {epoch + 1}, Training Loss: {total_loss / len(train_loader):.4f}")

# Оценка модели
model.eval()
predictions, true_labels = [], []
with torch.no_grad():
    for batch in test_loader:
        input_ids, attention_mask, labels = batch["input_ids"].to(device), batch["attention_mask"].to(device), batch[
            "labels"].to(device)
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
        preds = torch.argmax(logits, dim=1).cpu().numpy()
        predictions.extend(preds)
        true_labels.extend(labels.cpu().numpy())

accuracy = accuracy_score(true_labels, predictions)
precision = precision_score(true_labels, predictions)
recall = recall_score(true_labels, predictions)
f1 = f1_score(true_labels, predictions)

print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-score: {f1:.4f}")

# Сохранение модели
model.save_pretrained("../fraud_detection_module/model/distilbert_model")
tokenizer.save_pretrained("../fraud_detection_module/model/tokenizer")
