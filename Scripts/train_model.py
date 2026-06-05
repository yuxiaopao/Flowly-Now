#!/usr/bin/env python3
"""
Model training script with PyTorch environment check.
Receives config via --config JSON file and outputs streaming JSON logs to stdout.
Expected JSON event types: epoch_start, epoch_complete, training_complete, error, info, cancelled
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path


def _emit(event_type: str, **kwargs):
    """Emit a JSON event line to stdout."""
    payload = {"type": event_type, **kwargs}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _check_or_install_deps():
    """Check for torch/transformers; install if missing."""
    import importlib.util

    deps = {
        "torch": "torch",
        "torchvision": " torchvision",
        "transformers": " transformers",
    }

    for pkg, pip_name in deps.items():
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            _emit("info", message=f"[ENV] {pkg} not found, installing...")
            import subprocess

            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_name, "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _emit("info", message=f"[ENV] {pkg} installed successfully.")
            except subprocess.CalledProcessError as e:
                _emit("error", message=f"[ENV] Failed to install {pkg}: {e}")
                sys.exit(1)

    import torch

    _emit(
        "info",
        message=f"[ENV] PyTorch {torch.__version__}, CUDA available: {torch.cuda.is_available()}",
    )
    return torch


def _train_pytorch(config: dict) -> dict:
    """Train a PyTorch model (MNIST classifier as baseline)."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    import torchvision.datasets as dsets
    import torchvision.transforms as transforms

    torch.manual_seed(42)

    input_dim = config.get("input_dim", 784)
    hidden_dims = config.get("hidden_dims", [256, 128])
    output_dim = config.get("output_dim", 10)
    epochs = config.get("epochs", 10)
    batch_size = config.get("batch_size", 64)
    learning_rate = config.get("learning_rate", 0.001)
    dropout = config.get("dropout", 0.2)
    output_dir = config.get("output_dir", "./outputs")
    dataset_path = config.get("dataset_path", "")

    os.makedirs(output_dir, exist_ok=True)

    _emit("info", message="[TRAIN] Downloading / loading dataset...")

    try:
        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
        )
        train_dataset = dsets.MNIST(root=os.path.join(output_dir, "data"), train=True, download=True, transform=transform)
        test_dataset = dsets.MNIST(root=os.path.join(output_dir, "data"), train=False, download=True, transform=transform)
    except Exception:
        _emit("info", message="[TRAIN] Using synthetic dataset...")
        X = torch.randn(60000, input_dim)
        y = torch.randint(0, output_dim, (60000,))
        train_dataset = TensorDataset(X, y)
        X_test = torch.randn(10000, input_dim)
        y_test = torch.randint(0, output_dim, (10000,))
        test_dataset = TensorDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    layers = [nn.Flatten()]
    prev_dim = input_dim
    for h_dim in hidden_dims:
        layers.append(nn.Linear(prev_dim, h_dim))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(dropout))
        prev_dim = h_dim
    layers.append(nn.Linear(prev_dim, output_dim))

    model = nn.Sequential(*layers)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    _emit(
        "info",
        message=f"[TRAIN] Model: {' '.join([str(x).__class__.__name__ for x in model])} | Device: {device}",
    )

    best_val_acc = 0.0
    training_history = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0
        correct = 0
        total = 0

        _emit(
            "epoch_start",
            epoch=epoch,
            total_epochs=epochs,
            progress=int(epoch / epochs * 100),
        )

        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)

            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            pred = output.argmax(dim=1)
            correct += (pred == target).sum().item()
            total += target.size(0)

        train_loss = total_loss / len(train_loader)
        train_acc = correct / total

        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                val_loss += criterion(output, target).item()
                pred = output.argmax(dim=1)
                val_correct += (pred == target).sum().item()
                val_total += target.size(0)

        val_loss /= len(test_loader)
        val_acc = val_correct / val_total

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            model_path = os.path.join(output_dir, "best_model.pth")
            torch.save(model.state_dict(), model_path)

        history_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 6),
            "val_acc": round(val_acc, 4),
        }
        training_history.append(history_entry)

        _emit(
            "epoch_complete",
            epoch=epoch,
            total_epochs=epochs,
            train_loss=round(train_loss, 6),
            train_acc=round(train_acc, 4),
            val_loss=round(val_loss, 6),
            val_acc=round(val_acc, 4),
            progress=int(epoch / epochs * 100),
        )

    final_model_path = os.path.join(output_dir, "final_model.pth")
    torch.save(model.state_dict(), final_model_path)

    return {
        "model_path": final_model_path,
        "best_val_acc": round(best_val_acc, 4),
        "training_history": training_history,
    }


def _train_transformers(config: dict) -> dict:
    """Train a HuggingFace Transformers model."""
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        Trainer,
        TrainingArguments,
        datasets,
    )
    import numpy as np

    torch.manual_seed(42)

    model_name = config.get("model_name", "distilbert-base-uncased")
    num_labels = config.get("num_labels", 2)
    epochs = config.get("epochs", 3)
    batch_size = config.get("batch_size", 16)
    learning_rate = config.get("learning_rate", 2e-5)
    warmup_steps = config.get("warmup_steps", 100)
    weight_decay = config.get("weight_decay", 0.01)
    output_dir = config.get("output_dir", "./outputs")
    dataset_name = config.get("dataset_name", "imdb")

    os.makedirs(output_dir, exist_ok=True)

    _emit("info", message=f"[TRAIN] Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=num_labels
    )

    _emit("info", message=f"[TRAIN] Loading dataset: {dataset_name}")
    try:
        raw_datasets = datasets.load_dataset(dataset_name)
    except Exception:
        _emit("info", message="[TRAIN] Dataset load failed, using dummy data")
        raw_datasets = datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {"text": ["hello world"] * 100, "label": [0] * 100}
                ),
                "test": datasets.Dataset.from_dict(
                    {"text": ["hello world"] * 20, "label": [0] * 20}
                ),
            }
        )

    def tokenize(batch):
        return tokenizer(batch["text"], padding=True, truncation=True, max_length=512)

    tokenized_datasets = raw_datasets.map(tokenize, batched=True)
    tokenized_datasets.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=weight_decay,
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets.get("test", tokenized_datasets["train"]),
    )

    for epoch in range(1, epochs + 1):
        _emit(
            "epoch_start",
            epoch=epoch,
            total_epochs=epochs,
            progress=int(epoch / epochs * 100),
        )
        trainer.train()
        eval_result = trainer.evaluate()
        _emit(
            "epoch_complete",
            epoch=epoch,
            total_epochs=epochs,
            train_loss=eval_result.get("eval_loss", 0),
            train_acc=eval_result.get("eval_accuracy", 0),
            val_loss=eval_result.get("eval_loss", 0),
            val_acc=eval_result.get("eval_accuracy", 0),
            progress=int(epoch / epochs * 100),
        )

    model_path = os.path.join(output_dir, "final_model")
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)

    return {
        "model_path": model_path,
        "best_val_acc": 0.0,
        "training_history": [],
    }


def main():
    parser = argparse.ArgumentParser(description="Flowly Model Training Script")
    parser.add_argument("--config", required=True, help="Path to training config JSON")
    parser.add_argument("--job-id", required=True, help="Training job UUID")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    parser.add_argument(
        "--streaming", action="store_true", help="Enable streaming JSON output"
    )
    args = parser.parse_args()

    _emit("info", message=f"[START] Job {args.job_id} initializing...")
    start_time = time.time()

    try:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        _emit("error", message=f"[CONFIG] Failed to load config: {e}")
        sys.exit(1)

    if args.output_dir:
        config["output_dir"] = args.output_dir

    _check_or_install_deps()

    framework = config.get("framework", "pytorch")
    _emit("info", message=f"[TRAIN] Framework: {framework}")

    try:
        if framework == "pytorch":
            result = _train_pytorch(config)
        elif framework == "transformers":
            result = _train_transformers(config)
        else:
            _emit("error", message=f"[ERROR] Unsupported framework: {framework}")
            sys.exit(1)
    except Exception as e:
        import traceback

        _emit("error", message=f"[TRAIN] Training failed: {e}\n{traceback.format_exc()}")
        sys.exit(1)

    total_time = time.time() - start_time
    _emit(
        "training_complete",
        model_path=result["model_path"],
        best_val_acc=result["best_val_acc"],
        total_time=round(total_time, 2),
        training_history=result.get("training_history", []),
    )
    _emit("info", message=f"[DONE] Job {args.job_id} finished in {total_time:.1f}s")


if __name__ == "__main__":
    main()
