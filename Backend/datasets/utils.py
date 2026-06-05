"""
Utility functions for datasets app.
"""

import os
import json
import csv
import io
import hashlib
import tempfile
import logging
from typing import Dict, Any, List, Optional, Tuple

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

DATASET_STORAGE_DIR = getattr(settings, 'DATASET_STORAGE_DIR', os.path.join(settings.MEDIA_ROOT, 'datasets'))


def ensure_storage_dir():
    """Ensure the dataset storage directory exists."""
    os.makedirs(DATASET_STORAGE_DIR, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return os.path.splitext(filename)[1].lower().lstrip('.')


def detect_format_from_extension(filename: str, fallback_format: str = 'csv') -> str:
    """Detect file format from extension."""
    ext = get_file_extension(filename)
    format_map = {
        'txt': 'text',
        'csv': 'csv',
        'json': 'json',
        'jsonl': 'json',
        'parquet': 'parquet',
        'pq': 'parquet',
    }
    return format_map.get(ext, fallback_format)


def download_from_url(url: str, dest_path: str = None, timeout: int = 300) -> Tuple[str, int]:
    """
    Download a file from URL to local storage.

    Args:
        url: The URL to download from
        dest_path: Optional destination path. If not provided, a temp path is created.
        timeout: Download timeout in seconds

    Returns:
        Tuple of (file_path, file_size)
    """
    ensure_storage_dir()

    if dest_path is None:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        dest_path = os.path.join(DATASET_STORAGE_DIR, f"url_{url_hash}_{int(os.times().elapsed * 1000)}")

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream('GET', url) as response:
                response.raise_for_status()

                total_size = 0
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        total_size += len(chunk)

                return dest_path, total_size

    except httpx.HTTPError as e:
        logger.error(f"Failed to download from URL: {url}, error: {str(e)}")
        raise


def parse_dataset_file(file_path: str, format: str = 'csv', max_rows: int = 100) -> Dict[str, Any]:
    """
    Parse a dataset file and return preview data.

    Args:
        file_path: Path to the dataset file
        format: File format (csv, json, text, parquet)
        max_rows: Maximum number of rows to return for preview

    Returns:
        Dictionary with columns, rows, and statistics
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    format = format.lower()
    if format == 'text':
        return _parse_text_file(file_path, max_rows)
    elif format == 'csv':
        return _parse_csv_file(file_path, max_rows)
    elif format == 'json':
        return _parse_json_file(file_path, max_rows)
    elif format == 'parquet':
        return _parse_parquet_file(file_path, max_rows)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _parse_text_file(file_path: str, max_rows: int = 100) -> Dict[str, Any]:
    """Parse a plain text file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                lines.append(line.rstrip('\n\r'))

        total_lines = sum(1 for _ in open(file_path, 'r', encoding='utf-8', errors='ignore'))

        return {
            'columns': [{'name': 'text', 'type': 'string', 'sample': lines[0] if lines else ''}],
            'rows': [[line] for line in lines],
            'row_count': total_lines,
            'preview_rows': len(lines),
            'total_rows': total_lines,
        }
    except Exception as e:
        logger.error(f"Failed to parse text file: {file_path}, error: {str(e)}")
        raise


def _parse_csv_file(file_path: str, max_rows: int = 100) -> Dict[str, Any]:
    """Parse a CSV file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            rows = []
            columns = []

            for i, row in enumerate(reader):
                if i == 0:
                    columns = [{'name': col, 'type': 'string', 'sample': ''} for col in row]
                else:
                    rows.append(row)
                    if len(rows) >= max_rows:
                        break

        total_rows = sum(1 for _ in open(file_path, 'r', encoding='utf-8', errors='ignore')) - 1

        for col_idx, col in enumerate(columns):
            if rows and col_idx < len(rows[0]):
                col['sample'] = str(rows[0][col_idx])

        return {
            'columns': columns,
            'rows': rows,
            'row_count': total_rows,
            'preview_rows': len(rows),
            'total_rows': total_rows,
        }
    except Exception as e:
        logger.error(f"Failed to parse CSV file: {file_path}, error: {str(e)}")
        raise


def _parse_json_file(file_path: str, max_rows: int = 100) -> Dict[str, Any]:
    """Parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)

        if isinstance(data, list):
            rows = data[:max_rows]
            total_rows = len(data)

            if rows and isinstance(rows[0], dict):
                columns = [
                    {'name': key, 'type': 'string', 'sample': str(rows[0].get(key, ''))}
                    for key in rows[0].keys()
                ]
                rows = [[row.get(col['name'], '') for col in columns] for row in rows]
            elif rows:
                columns = [{'name': 'value', 'type': 'string', 'sample': str(rows[0])}]
                rows = [[val] for val in rows]
            else:
                columns = []
                rows = []

        elif isinstance(data, dict):
            rows = [[json.dumps(data, ensure_ascii=False)]]
            columns = [{'name': 'data', 'type': 'object', 'sample': json.dumps(data, ensure_ascii=False)[:100]}]
            total_rows = 1
        else:
            raise ValueError("JSON file must contain an array or object")

        return {
            'columns': columns,
            'rows': rows,
            'row_count': total_rows,
            'preview_rows': len(rows),
            'total_rows': total_rows,
        }
    except Exception as e:
        logger.error(f"Failed to parse JSON file: {file_path}, error: {str(e)}")
        raise


def _parse_parquet_file(file_path: str, max_rows: int = 100) -> Dict[str, Any]:
    """Parse a Parquet file."""
    try:
        import pandas as pd

        df = pd.read_parquet(file_path)
        total_rows = len(df)

        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'int' in dtype:
                col_type = 'integer'
            elif 'float' in dtype:
                col_type = 'float'
            elif 'bool' in dtype:
                col_type = 'boolean'
            else:
                col_type = 'string'
            columns.append({
                'name': col,
                'type': col_type,
                'sample': str(df[col].iloc[0]) if len(df) > 0 else ''
            })

        preview_df = df.head(max_rows)
        rows = preview_df.values.tolist()
        rows = [[None if pd.isna(val) else val for val in row] for row in rows]

        return {
            'columns': columns,
            'rows': rows,
            'row_count': total_rows,
            'preview_rows': len(rows),
            'total_rows': total_rows,
        }
    except ImportError:
        raise ImportError("pandas and pyarrow are required to parse Parquet files")
    except Exception as e:
        logger.error(f"Failed to parse Parquet file: {file_path}, error: {str(e)}")
        raise


def detect_columns_and_stats(file_path: str, format: str = 'csv', max_rows: int = 1000) -> Dict[str, Any]:
    """
    Detect columns and compute basic statistics for a dataset file.

    Args:
        file_path: Path to the dataset file
        format: File format
        max_rows: Maximum rows to analyze for statistics

    Returns:
        Dictionary with column info, row count, and basic stats
    """
    preview_data = parse_dataset_file(file_path, format, max_rows)

    columns = preview_data['columns']
    rows = preview_data['rows']

    stats = {
        'columns': columns,
        'column_count': len(columns),
        'row_count': preview_data['row_count'],
        'preview_rows': preview_data['preview_rows'],
    }

    if rows and columns:
        null_counts = {}
        unique_counts = {}
        numeric_stats = {}

        for col_idx, col in enumerate(columns):
            col_values = [row[col_idx] if col_idx < len(row) else None for row in rows]
            non_null_values = [v for v in col_values if v is not None and v != '']

            null_counts[col['name']] = len(col_values) - len(non_null_values)
            unique_counts[col['name']] = len(set(str(v) for v in non_null_values))

            if col['type'] in ('integer', 'float'):
                try:
                    numeric_values = [float(v) for v in non_null_values if v is not None]
                    if numeric_values:
                        numeric_stats[col['name']] = {
                            'min': min(numeric_values),
                            'max': max(numeric_values),
                            'mean': sum(numeric_values) / len(numeric_values),
                            'count': len(numeric_values)
                        }
                except (ValueError, TypeError):
                    pass

        stats['null_counts'] = null_counts
        stats['unique_counts'] = unique_counts
        stats['numeric_stats'] = numeric_stats

    return stats


def get_dataset_file_stats(file_path: str, format: str = 'csv') -> Dict[str, Any]:
    """
    Get comprehensive statistics for a dataset file.

    Args:
        file_path: Path to the dataset file
        format: File format

    Returns:
        Dictionary with file statistics
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)

    stats = detect_columns_and_stats(file_path, format, max_rows=1000)

    return {
        'size_bytes': file_size,
        'size_display': format_bytes(file_size),
        'format': format,
        **stats
    }


def format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def process_s3_path(s3_path: str) -> Tuple[str, str]:
    """
    Parse S3 path into bucket and key.

    Args:
        s3_path: S3 path in format s3://bucket/key or bucket/key

    Returns:
        Tuple of (bucket, key)
    """
    if s3_path.startswith('s3://'):
        s3_path = s3_path[5:]

    parts = s3_path.split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ''

    return bucket, key


def download_from_s3(s3_path: str, dest_path: str = None) -> Tuple[str, int]:
    """
    Download a file from S3 to local storage.

    Args:
        s3_path: S3 path in format s3://bucket/key
        dest_path: Optional destination path

    Returns:
        Tuple of (file_path, file_size)
    """
    try:
        import boto3
    except ImportError:
        raise ImportError("boto3 is required for S3 support. Install with: pip install boto3")

    bucket, key = process_s3_path(s3_path)

    ensure_storage_dir()

    if dest_path is None:
        dest_path = os.path.join(DATASET_STORAGE_DIR, f"s3_{bucket}_{key.replace('/', '_')}")

    try:
        s3_client = boto3.client('s3')
        s3_client.download_file(bucket, key, dest_path)
        file_size = os.path.getsize(dest_path)
        return dest_path, file_size
    except Exception as e:
        logger.error(f"Failed to download from S3: {s3_path}, error: {str(e)}")
        raise
