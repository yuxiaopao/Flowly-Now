"""
Training Runner
Executes model training with progress reporting.
"""

import json
import os
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TrainingRunner:
    """
    Runs training and reports progress via callbacks.
    
    Supports PyTorch and HuggingFace Transformers training with real-time
    progress updates through callbacks and file-based state sharing.
    """
    
    def __init__(
        self, 
        job_id: str, 
        config: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize the training runner.
        
        Args:
            job_id: Unique job identifier
            config: Training configuration dictionary
            progress_callback: Callback function for progress updates
            output_dir: Output directory for checkpoints and models
        """
        self.job_id = job_id
        self.config = config
        self.progress_callback = progress_callback or (lambda **kw: None)
        self.output_dir = Path(output_dir or config.get('output_dir', f'./outputs/{job_id}'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._cancelled = False
        self._paused = False
        self._stop_event = threading.Event()
        
        self._gpu_info = None
        self._device = None
        
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    @property
    def is_paused(self) -> bool:
        return self._paused
    
    def cancel(self):
        """Signal the training to stop."""
        self._cancelled = True
        self._stop_event.set()
    
    def pause(self):
        """Signal the training to pause."""
        self._paused = True
        self._stop_event.set()
    
    def resume(self):
        """Resume the training."""
        self._paused = False
        self._stop_event.clear()
    
    def detect_gpu(self) -> Dict[str, Any]:
        """
        Detect GPU availability using torch.cuda.
        
        Returns:
            Dict with GPU info or availability status
        """
        if self._gpu_info is not None:
            return self._gpu_info
        
        gpu_info = {'available': False}
        
        try:
            import torch
            
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                gpu_info = {
                    'available': True,
                    'device_count': device_count,
                    'name': torch.cuda.get_device_name(0),
                    'total_memory': torch.cuda.get_device_properties(0).total_memory,
                }
                
                try:
                    if hasattr(torch.cuda, 'mem_get_info'):
                        free, total = torch.cuda.mem_get_info(0)
                        gpu_info['memory_free'] = free
                        gpu_info['memory_total'] = total
                        gpu_info['memory_used'] = total - free
                except Exception:
                    pass
                
                self._device = f'cuda:0'
            else:
                self._device = 'cpu'
                
        except ImportError:
            logger.warning('PyTorch not installed, GPU detection failed')
            self._device = 'cpu'
        except Exception as e:
            logger.warning(f'GPU detection failed: {e}')
            self._device = 'cpu'
        
        self._gpu_info = gpu_info
        return gpu_info
    
    def _write_progress_file(self, data: Dict[str, Any]):
        """Write progress to shared JSON file for polling."""
        try:
            progress_file = self.output_dir / 'progress.json'
            with open(progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f'Failed to write progress file: {e}')
    
    def _write_status_file(self, status: str, **kwargs):
        """Write status to shared JSON file."""
        try:
            status_file = self.output_dir / 'status.json'
            data = {
                'status': status,
                'job_id': self.job_id,
                'timestamp': datetime.now().isoformat(),
                **kwargs
            }
            with open(status_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f'Failed to write status file: {e}')
    
    def _emit_progress(self, **kwargs):
        """Emit progress update via callback."""
        kwargs['job_id'] = self.job_id
        self.progress_callback(**kwargs)
        self._write_progress_file(kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Run the training based on framework.
        
        Returns:
            Training result dictionary
        """
        framework = self.config.get('framework', 'pytorch')
        
        if self._cancelled:
            return {'success': False, 'error': 'Job was cancelled before starting'}
        
        self._write_status_file('running', gpu=self.detect_gpu()['available'])
        
        try:
            if framework == 'pytorch':
                return self.run_pytorch_training()
            elif framework == 'transformers':
                return self.run_transformers_training()
            elif framework == 'keras':
                return self.run_keras_training()
            elif framework == 'tensorflow':
                return self.run_tensorflow_training()
            else:
                raise ValueError(f'Unsupported framework: {framework}')
        except Exception as e:
            logger.exception(f'Training failed: {e}')
            self._write_status_file('failed', error=str(e))
            return {'success': False, 'error': str(e)}
    
    def run_pytorch_training(self) -> Dict[str, Any]:
        """
        Real PyTorch training loop with progress reporting.
        
        Returns:
            Training result with metrics and paths
        """
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, TensorDataset
        import numpy as np
        import pandas as pd
        
        logger.info(f'Starting PyTorch training for job {self.job_id}')
        
        device = self._device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._emit_progress(device=device, status='loading_data')
        
        epochs = self.config.get('epochs', 10)
        batch_size = self.config.get('batch_size', 32)
        learning_rate = self.config.get('learning_rate', 0.001)
        input_dim = self.config.get('input_dim', 784)
        hidden_dims = self.config.get('hidden_dims', [256, 128])
        output_dim = self.config.get('output_dim', 10)
        dropout = self.config.get('dropout', 0.2)
        dataset_path = self.config.get('dataset_path', '')
        
        self._emit_progress(total_epochs=epochs)
        
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        
        model = nn.Sequential(*layers).to(device)
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        if dataset_path and Path(dataset_path).exists():
            ext = Path(dataset_path).suffix.lower()
            if ext == '.csv':
                df = pd.read_csv(dataset_path)
                X = df.iloc[:, :-1].values.astype(np.float32)
                y = df.iloc[:, -1].values.astype(np.int64)
            elif ext == '.json':
                with open(dataset_path, 'r') as f:
                    data = json.load(f)
                X = np.array(data.get('features', [])).astype(np.float32)
                y = np.array(data.get('labels', [])).astype(np.int64)
            else:
                raise ValueError(f'Unsupported dataset format: {ext}')
            
            X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)
            
            dataset = TensorDataset(
                torch.tensor(X, dtype=torch.float32),
                torch.tensor(y, dtype=torch.int64)
            )
        else:
            logger.info('No dataset provided, using simulated data')
            num_samples = 1000
            X = np.random.randn(num_samples, input_dim).astype(np.float32)
            y = np.random.randint(0, output_dim, size=num_samples).astype(np.int64)
            
            dataset = TensorDataset(
                torch.tensor(X, dtype=torch.float32),
                torch.tensor(y, dtype=torch.int64)
            )
        
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        total_steps = len(dataloader)
        
        self._emit_progress(total_steps=total_steps, status='training')
        
        all_losses = []
        all_metrics = []
        history = []
        best_loss = float('inf')
        
        for epoch in range(epochs):
            if self._cancelled:
                self._write_status_file('cancelled')
                return {'success': False, 'error': 'Job was cancelled', 'cancelled': True}
            
            while self._paused:
                time.sleep(0.5)
                if self._cancelled:
                    self._write_status_file('cancelled')
                    return {'success': False, 'error': 'Job was cancelled', 'cancelled': True}
            
            model.train()
            epoch_losses = []
            all_preds = []
            all_labels = []
            
            for step, (batch_X, batch_y) in enumerate(dataloader):
                if self._cancelled:
                    break
                
                while self._paused:
                    time.sleep(0.5)
                    if self._cancelled:
                        break
                
                batch_X = batch_X.to(device)
                batch_y = batch_y.to(device)
                
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                epoch_losses.append(loss.item())
                all_preds.extend(outputs.argmax(dim=1).cpu().numpy())
                all_labels.extend(batch_y.cpu().numpy())
                
                progress = ((epoch * total_steps + step + 1) / (epochs * total_steps)) * 100
                self._emit_progress(
                    epoch=epoch + 1,
                    step=step + 1,
                    total_steps=total_steps,
                    loss=loss.item(),
                    progress=progress
                )
            
            avg_loss = np.mean(epoch_losses)
            accuracy = np.mean(np.array(all_preds) == np.array(all_labels))
            
            metrics = {'accuracy': float(accuracy), 'loss': float(avg_loss)}
            all_losses.append(avg_loss)
            all_metrics.append(metrics)
            
            history.append({
                'epoch': epoch + 1,
                'loss': float(avg_loss),
                'accuracy': float(accuracy),
                'lr': optimizer.param_groups[0]['lr'],
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f'Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}')
            
            checkpoint_path = self.output_dir / f'checkpoint_epoch_{epoch + 1}.pt'
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': avg_loss,
                'metrics': metrics,
            }, checkpoint_path)
            
            if avg_loss < best_loss:
                best_loss = avg_loss
                best_model_path = self.output_dir / 'best_model.pt'
                torch.save({
                    'model_state_dict': model.state_dict(),
                    'config': self.config,
                    'final_metrics': metrics,
                }, best_model_path)
        
        final_model_path = self.output_dir / 'model.pt'
        torch.save({
            'model_state_dict': model.state_dict(),
            'config': self.config,
            'final_metrics': all_metrics[-1] if all_metrics else {},
        }, final_model_path)
        
        history_path = self.output_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        self._write_status_file('completed')
        self._emit_progress(
            status='completed',
            progress=100,
            history=history,
            final_metric=all_metrics[-1] if all_metrics else {}
        )
        
        result = {
            'success': True,
            'output_dir': str(self.output_dir),
            'model_path': str(final_model_path),
            'best_model_path': str(self.output_dir / 'best_model.pt'),
            'total_epochs': epochs,
            'final_loss': all_losses[-1] if all_losses else 0,
            'final_metrics': all_metrics[-1] if all_metrics else {},
            'history': history,
        }
        
        logger.info(f'PyTorch training completed for job {self.job_id}')
        return result
    
    def run_transformers_training(self) -> Dict[str, Any]:
        """
        Real HuggingFace Transformers training with progress.
        
        Returns:
            Training result with metrics and paths
        """
        try:
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                TrainingArguments,
                Trainer,
            )
        except ImportError:
            return {
                'success': False,
                'error': 'transformers not installed. Run: pip install transformers datasets accelerate'
            }
        
        logger.info(f'Starting Transformers training for job {self.job_id}')
        
        import torch
        import numpy as np
        
        device = self._device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._emit_progress(device=device, status='loading_data')
        
        model_name = self.config.get('model_name', 'bert-base-uncased')
        dataset_name = self.config.get('dataset_name', '')
        dataset_path = self.config.get('dataset_path', '')
        num_labels = self.config.get('num_labels', 2)
        epochs = self.config.get('epochs', 3)
        batch_size = self.config.get('batch_size', 8)
        learning_rate = self.config.get('learning_rate', 2e-5)
        
        self._emit_progress(total_epochs=epochs)
        
        if dataset_name:
            try:
                from datasets import load_dataset
                dataset = load_dataset(dataset_name)
            except Exception as e:
                return {'success': False, 'error': f'Failed to load dataset {dataset_name}: {str(e)}'}
        elif dataset_path:
            from datasets import load_dataset
            ext = Path(dataset_path).suffix.lower()
            if ext == '.csv':
                dataset = load_dataset('csv', data_files=dataset_path)
            elif ext == '.json':
                dataset = load_dataset('json', data_files=dataset_path)
            else:
                return {'success': False, 'error': f'Unsupported dataset format: {ext}'}
        else:
            return {'success': False, 'error': 'dataset_name or dataset_path is required'}
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=num_labels,
            )
        except Exception as e:
            return {'success': False, 'error': f'Failed to load model {model_name}: {str(e)}'}
        
        text_column = 'text' if 'text' in dataset['train'].column_names else 'input'
        if text_column not in dataset['train'].column_names:
            return {'success': False, 'error': f'Dataset must have a text column'}
        
        def preprocess_function(examples):
            return tokenizer(
                examples[text_column],
                truncation=True,
                padding='max_length',
                max_length=512,
            )
        
        train_dataset = dataset['train'].map(preprocess_function, batched=True)
        eval_dataset = None
        if 'validation' in dataset:
            eval_dataset = dataset['validation'].map(preprocess_function, batched=True)
        elif 'test' in dataset:
            eval_dataset = dataset['test'].map(preprocess_function, batched=True)
        
        def compute_metrics_transformers(eval_pred):
            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=-1)
            return {'accuracy': float((predictions == labels).mean())}
        
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=100,
            weight_decay=0.01,
            eval_strategy='epoch' if eval_dataset else 'no',
            save_strategy='epoch',
            load_best_model_at_end=True if eval_dataset else False,
            metric_for_best_model='accuracy',
            greater_is_better=True,
            save_total_limit=3,
            logging_dir=str(self.output_dir / 'logs'),
            logging_steps=10,
            fp16=torch.cuda.is_available(),
            report_to=['none'],
        )
        
        self._emit_progress(status='training')
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            compute_metrics=compute_metrics_transformers,
        )
        
        class ProgressCallback:
            def __init__(self, runner):
                self.runner = runner
                self.current_epoch = 0
            
            def on_step_end(self, args, state, control, **kwargs):
                if state.global_step % 10 == 0:
                    progress = (state.global_step / state.max_steps) * 100 if state.max_steps else 0
                    self.runner._emit_progress(
                        step=state.global_step,
                        total_steps=state.max_steps,
                        progress=progress,
                        epoch=state.epoch
                    )
            
            def on_epoch_end(self, args, state, control, **kwargs):
                self.current_epoch = int(state.epoch)
                self.runner._emit_progress(epoch=self.current_epoch)
        
        progress_cb = ProgressCallback(self)
        trainer.add_callback(progress_cb)
        
        try:
            trainer.train()
        except Exception as e:
            if self._cancelled:
                return {'success': False, 'error': 'Job was cancelled', 'cancelled': True}
            raise
        
        if self._cancelled:
            return {'success': False, 'error': 'Job was cancelled', 'cancelled': True}
        
        final_model_path = self.output_dir / 'final_model'
        model.save_pretrained(final_model_path)
        tokenizer.save_pretrained(final_model_path)
        
        history_path = self.output_dir / 'training_history.json'
        history = [{'epoch': i + 1, 'metrics': {'accuracy': m}} for i, m in enumerate(trainer.state.log_history) if 'eval_accuracy' in m]
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        self._write_status_file('completed')
        
        result = {
            'success': True,
            'output_dir': str(self.output_dir),
            'model_path': str(final_model_path),
            'total_epochs': epochs,
            'history': history,
        }
        
        if eval_dataset:
            eval_metrics = trainer.evaluate()
            result['final_metrics'] = eval_metrics
        
        logger.info(f'Transformers training completed for job {self.job_id}')
        return result
    
    def run_keras_training(self) -> Dict[str, Any]:
        """
        Keras training implementation.
        
        Returns:
            Training result with metrics and paths
        """
        try:
            import tensorflow as tf
            from tensorflow import keras
        except ImportError:
            return {'success': False, 'error': 'TensorFlow/Keras not installed'}
        
        logger.info(f'Starting Keras training for job {self.job_id}')
        
        epochs = self.config.get('epochs', 10)
        batch_size = self.config.get('batch_size', 32)
        learning_rate = self.config.get('learning_rate', 0.001)
        
        self._emit_progress(total_epochs=epochs, status='preparing')
        
        input_dim = self.config.get('input_dim', 784)
        output_dim = self.config.get('output_dim', 10)
        
        model = keras.Sequential([
            keras.layers.Dense(256, activation='relu', input_shape=(input_dim,)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(output_dim, activation='softmax')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        dataset_path = self.config.get('dataset_path', '')
        if dataset_path and Path(dataset_path).exists():
            import pandas as pd
            import numpy as np
            
            ext = Path(dataset_path).suffix.lower()
            if ext == '.csv':
                df = pd.read_csv(dataset_path)
                X = df.iloc[:, :-1].values.astype(np.float32)
                y = df.iloc[:, -1].values.astype(np.int64)
            else:
                return {'success': False, 'error': f'Unsupported dataset format: {ext}'}
        else:
            num_samples = 1000
            X = np.random.randn(num_samples, input_dim).astype(np.float32)
            y = np.random.randint(0, output_dim, size=num_samples).astype(np.int64)
        
        self._emit_progress(status='training')
        
        class KerasProgressCallback(keras.callbacks.Callback):
            def __init__(self, runner):
                super().__init__()
                self.runner = runner
            
            def on_epoch_end(self, epoch, logs=None):
                logs = logs or {}
                self.runner._emit_progress(
                    epoch=epoch + 1,
                    loss=logs.get('loss'),
                    metric=logs.get('accuracy'),
                    progress=((epoch + 1) / self.runner.config.get('epochs', 10)) * 100
                )
        
        model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[KerasProgressCallback(self)],
            verbose=1
        )
        
        final_model_path = self.output_dir / 'model.keras'
        model.save(final_model_path)
        
        history_path = self.output_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump({'history': 'see model.history'}, f)
        
        self._write_status_file('completed')
        
        return {
            'success': True,
            'output_dir': str(self.output_dir),
            'model_path': str(final_model_path),
            'total_epochs': epochs,
        }
    
    def run_tensorflow_training(self) -> Dict[str, Any]:
        """
        TensorFlow training implementation (alias for Keras).
        
        Returns:
            Training result with metrics and paths
        """
        return self.run_keras_training()


def run_training_in_thread(
    job_id: str,
    config: Dict[str, Any],
    progress_callback: Callable,
    output_dir: Optional[str] = None
) -> threading.Thread:
    """
    Run training in a background thread.
    
    Args:
        job_id: Unique job identifier
        config: Training configuration
        progress_callback: Callback for progress updates
        output_dir: Output directory for results
        
    Returns:
        The thread running the training
    """
    runner = TrainingRunner(job_id, config, progress_callback, output_dir)
    
    def run():
        try:
            result = runner.run()
            logger.info(f'Training job {job_id} finished: {result}')
        except Exception as e:
            logger.exception(f'Training job {job_id} crashed: {e}')
            progress_callback(job_id=job_id, status='failed', error=str(e))
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    return thread
