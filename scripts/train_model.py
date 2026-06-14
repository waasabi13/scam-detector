import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from transformers import (
    DistilBertForSequenceClassification,
    DistilBertTokenizer,
    get_linear_schedule_with_warmup,
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
PROJECT_DIR = BASE_DIR.parent

DATASET_PATH = PROJECT_DIR / "dataset" / "fraud_dataset.csv"

# ВАЖНО:
# старая рабочая модель остается в:
# backend/detector/model/distilbert_model
#
# новая экспериментальная модель сохраняется отдельно:
SAVE_PATH = (
    PROJECT_DIR
    / "backend"
    / "detector"
    / "model"
    / "distilbert_model_experimental"
)

REPORTS_DIR = PROJECT_DIR / "reports" / "training_results"


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
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# =========================
# Вспомогательные функции
# =========================

def print_class_distribution(title: str, dataframe: pd.DataFrame) -> None:
    print(title)
    print(f"Всего сообщений: {len(dataframe)}")
    print(
        dataframe["label"]
        .value_counts()
        .rename(index={0: "Не мошенничество", 1: "Мошенничество"})
    )
    print()


def save_loss_graph(train_losses):
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(train_losses) + 1), train_losses, marker="o")
    plt.title("Изменение функции потерь при обучении")
    plt.xlabel("Эпоха")
    plt.ylabel("Loss")
    plt.grid(True)

    path = REPORTS_DIR / "loss_graph.png"
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()

    return path


def save_accuracy_graph(epoch_accuracies):
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(epoch_accuracies) + 1), epoch_accuracies, marker="o")
    plt.title("Изменение точности на тестовой выборке")
    plt.xlabel("Эпоха")
    plt.ylabel("Accuracy")
    plt.grid(True)

    path = REPORTS_DIR / "accuracy_graph.png"
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()

    return path


def save_confusion_matrix_graph(cm):
    fig, ax = plt.subplots(figsize=(6, 5))

    image = ax.imshow(cm)

    ax.set_title("Матрица ошибок")
    ax.set_xlabel("Предсказанный класс")
    ax.set_ylabel("Истинный класс")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])

    ax.set_xticklabels(["Не мошенничество", "Мошенничество"])
    ax.set_yticklabels(["Не мошенничество", "Мошенничество"])

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                cm[i, j],
                ha="center",
                va="center",
                fontsize=12,
            )

    fig.colorbar(image)

    path = REPORTS_DIR / "confusion_matrix.png"
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()

    return path


def save_metrics_table(accuracy, precision, recall, f1):
    metrics = pd.DataFrame(
        {
            "Метрика": ["Accuracy", "Precision", "Recall", "F1-score"],
            "Значение": [
                round(accuracy, 4),
                round(precision, 4),
                round(recall, 4),
                round(f1, 4),
            ],
        }
    )

    path = REPORTS_DIR / "metrics_table.csv"
    metrics.to_csv(path, index=False, encoding="utf-8-sig")

    return path


def save_training_report(
    accuracy,
    precision,
    recall,
    f1,
    cm,
    report_text,
    train_size,
    test_size,
    initial_count,
    balanced_count,
    augmented_count,
):
    path = REPORTS_DIR / "training_report.txt"

    with open(path, "w", encoding="utf-8") as file:
        file.write("=== Параметры обучения ===\n")
        file.write(f"Модель: {MODEL_NAME}\n")
        file.write(f"Device: {device}\n")
        file.write(f"Epochs: {EPOCHS}\n")
        file.write(f"Batch size: {BATCH_SIZE}\n")
        file.write(f"Learning rate: {LEARNING_RATE}\n")
        file.write(f"Max sequence length: {MAX_LEN}\n\n")

        file.write("=== Размеры выборок ===\n")
        file.write(f"Исходный датасет: {initial_count}\n")
        file.write(f"После балансировки: {balanced_count}\n")
        file.write(f"После аугментации: {augmented_count}\n")
        file.write(f"Train: {train_size}\n")
        file.write(f"Test: {test_size}\n\n")

        file.write("=== Результаты оценки модели ===\n")
        file.write(f"Accuracy:  {accuracy:.4f}\n")
        file.write(f"Precision: {precision:.4f}\n")
        file.write(f"Recall:    {recall:.4f}\n")
        file.write(f"F1-score:  {f1:.4f}\n\n")

        file.write("=== Матрица ошибок ===\n")
        file.write("Строки — реальные классы, столбцы — предсказанные классы\n")
        file.write("Классы: 0 — не мошенничество, 1 — мошенничество\n")
        file.write(str(cm))
        file.write("\n\n")

        file.write("=== Classification Report ===\n")
        file.write(report_text)

    return path


# =========================
# Загрузка и подготовка данных
# =========================

if not DATASET_PATH.exists():
    raise FileNotFoundError(f"Датасет не найден: {DATASET_PATH}")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATASET_PATH)

required_columns = {"text", "label"}
if not required_columns.issubset(df.columns):
    raise ValueError("CSV-файл должен содержать колонки 'text' и 'label'.")

df = df.dropna(subset=["text", "label"])
df["text"] = df["text"].astype(str)
df["label"] = df["label"].astype(int)

df = df[df["label"].isin([0, 1])]

initial_count = len(df)

print_class_distribution("=== Исходный датасет ===", df)


# =========================
# Балансировка классов
# =========================

normal_df = df[df["label"] == 0]
fraud_df = df[df["label"] == 1]

if len(normal_df) > len(fraud_df):
    fraud_df = fraud_df.sample(
        n=len(normal_df),
        replace=True,
        random_state=SEED,
    )
elif len(fraud_df) > len(normal_df):
    normal_df = normal_df.sample(
        n=len(fraud_df),
        replace=True,
        random_state=SEED,
    )

df = pd.concat([normal_df, fraud_df])
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

balanced_count = len(df)

print_class_distribution("=== После балансировки ===", df)


# =========================
# Аугментация мошеннических сообщений
# =========================

augmented_rows = []

for _, row in df.iterrows():
    augmented_rows.append(
        {
            "text": row["text"],
            "label": int(row["label"]),
        }
    )

    if row["label"] == 1 and random.random() > 0.4:
        augmented_rows.append(
            {
                "text": augment_text(row["text"]),
                "label": int(row["label"]),
            }
        )

df = pd.DataFrame(augmented_rows)
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

augmented_count = len(df)

print_class_distribution("=== После аугментации ===", df)


# =========================
# Разделение на train/test
# =========================

train_texts, test_texts, train_labels, test_labels = train_test_split(
    df["text"],
    df["label"],
    test_size=0.2,
    stratify=df["label"],
    random_state=SEED,
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
    num_labels=2,
)

model.to(device)

train_dataset = FraudDataset(train_texts, train_labels, tokenizer, MAX_LEN)
test_dataset = FraudDataset(test_texts, test_labels, tokenizer, MAX_LEN)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
)


# =========================
# Loss, optimizer, scheduler
# =========================

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.array([0, 1]),
    y=df["label"],
)

class_weights = torch.tensor(
    class_weights,
    dtype=torch.float,
).to(device)

loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)

optimizer = AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
)

total_steps = len(train_loader) * EPOCHS

scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=0,
    num_training_steps=total_steps,
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
epoch_accuracies = []

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
            attention_mask=attention_mask,
        )

        loss = loss_fn(outputs.logits, labels)

        loss.backward()
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(train_loader)
    train_losses.append(avg_loss)

    model.eval()

    epoch_predictions = []
    epoch_true_labels = []

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )

            preds = torch.argmax(outputs.logits, dim=1)

            epoch_predictions.extend(preds.cpu().numpy())
            epoch_true_labels.extend(labels.cpu().numpy())

    epoch_accuracy = accuracy_score(epoch_true_labels, epoch_predictions)
    epoch_accuracies.append(epoch_accuracy)

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Training Loss: {avg_loss:.4f} | "
        f"Test Accuracy: {epoch_accuracy:.4f}"
    )


# =========================
# Финальная оценка модели
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
            attention_mask=attention_mask,
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

report_text = classification_report(
    true_labels,
    predictions,
    target_names=["Не мошенничество", "Мошенничество"],
    zero_division=0,
)


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
print(report_text)


# =========================
# Сохранение графиков и отчётов
# =========================

loss_path = save_loss_graph(train_losses)
accuracy_path = save_accuracy_graph(epoch_accuracies)
cm_path = save_confusion_matrix_graph(cm)
metrics_path = save_metrics_table(accuracy, precision, recall, f1)

report_path = save_training_report(
    accuracy=accuracy,
    precision=precision,
    recall=recall,
    f1=f1,
    cm=cm,
    report_text=report_text,
    train_size=len(train_texts),
    test_size=len(test_texts),
    initial_count=initial_count,
    balanced_count=balanced_count,
    augmented_count=augmented_count,
)


# =========================
# Сохранение модели
# =========================

SAVE_PATH.mkdir(parents=True, exist_ok=True)

model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)


print()
print(f"Модель и токенизатор сохранены в: {SAVE_PATH}")
print(f"График Loss сохранён: {loss_path}")
print(f"График Accuracy сохранён: {accuracy_path}")
print(f"Матрица ошибок сохранена: {cm_path}")
print(f"Таблица метрик сохранена: {metrics_path}")
print(f"Отчёт сохранён: {report_path}")