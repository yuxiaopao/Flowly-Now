"""
Real model evaluation logic.
"""

import os
import json
import numpy as np
from typing import Dict, Any, List


def evaluate_pytorch_classifier(model_path: str, test_data: List, labels: List[str]) -> Dict[str, float]:
    """
    Real PyTorch classifier evaluation.
    Loads the model and computes actual metrics.
    """
    try:
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model = checkpoint.get('model', checkpoint) if isinstance(checkpoint, dict) else checkpoint
        if hasattr(model, 'eval'):
            model = model.to(device)

        metrics = {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
        }

        if test_data:
            X_test = torch.tensor([d['features'] for d in test_data], dtype=torch.float32)
            y_test = torch.tensor([d['label'] for d in test_data], dtype=torch.long)

            test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size=32)

            correct = 0
            total = 0
            all_preds = []
            all_labels = []

            with torch.no_grad():
                for X_batch, y_batch in test_loader:
                    X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                    outputs = model(X_batch)
                    _, predicted = torch.max(outputs.data, 1)
                    total += y_batch.size(0)
                    correct += (predicted == y_batch).sum().item()
                    all_preds.extend(predicted.cpu().numpy())
                    all_labels.extend(y_batch.cpu().numpy())

            if total > 0:
                metrics['accuracy'] = round(correct / total, 4)

                from sklearn.metrics import precision_score, recall_score, f1_score
                if len(set(all_labels)) > 1:
                    metrics['precision'] = round(precision_score(all_labels, all_preds, average='weighted', zero_division=0), 4)
                    metrics['recall'] = round(recall_score(all_labels, all_preds, average='weighted', zero_division=0), 4)
                    metrics['f1'] = round(f1_score(all_labels, all_preds, average='weighted', zero_division=0), 4)

        return metrics

    except ImportError:
        raise ImportError('torch and sklearn are required for PyTorch evaluation')
    except FileNotFoundError:
        raise FileNotFoundError(f'Model not found: {model_path}')
    except Exception as e:
        raise RuntimeError(f'Evaluation failed: {str(e)}')


def evaluate_csv_classification(model_path: str, csv_path: str, label_col: str, features: List[str]) -> Dict[str, float]:
    """
    Evaluate a CSV file using a loaded model.
    """
    try:
        import pandas as pd
        import torch
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        df = pd.read_csv(csv_path)
        if label_col not in df.columns:
            raise ValueError(f'Label column {label_col} not found. Available: {list(df.columns)}')
        if not all(f in df.columns for f in features):
            raise ValueError(f'Some feature columns not found in CSV')

        X = df[features].values
        y_true = df[label_col].values

        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        model = checkpoint.get('model', checkpoint) if isinstance(checkpoint, dict) else checkpoint
        if hasattr(model, 'eval'):
            model.eval()

        X_tensor = torch.tensor(X, dtype=torch.float32)
        with torch.no_grad():
            outputs = model(X_tensor)
            _, y_pred = torch.max(outputs, 1)
            y_pred = y_pred.numpy()

        metrics = {
            'accuracy': round(accuracy_score(y_true, y_pred), 4),
            'precision': round(precision_score(y_true, y_pred, average='weighted', zero_division=0), 4),
            'recall': round(recall_score(y_true, y_pred, average='weighted', zero_division=0), 4),
            'f1': round(f1_score(y_true, y_pred, average='weighted', zero_division=0), 4),
        }

        return metrics

    except ImportError:
        raise ImportError('pandas, torch, and sklearn are required for CSV evaluation')
    except Exception as e:
        raise RuntimeError(f'CSV evaluation failed: {str(e)}')


def evaluate_mock(labels: List[str]) -> Dict[str, float]:
    """Fallback when no model file is available."""
    import random
    base = {l: random.uniform(0.75, 0.97) for l in labels}
    total = sum(base.values())
    base = {k: round(v / total, 4) for k, v in base.items()}
    return base
