"""Preprocessing metadata for the existing generic tabular training algorithm."""
SCHEMA_VERSION = 'flowly.tabular-preprocessing/v1'


def standardize_tabular_features(values, feature_names=None, label_column=None):
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    metadata = {'schema': SCHEMA_VERSION, 'kind': 'standardize', 'mean': mean.tolist(), 'std': std.tolist(),
        'feature_names': list(feature_names or []), 'label_column': label_column, 'epsilon': 1e-8}
    # This is the same normalization previously performed by both runners.
    return (values - mean) / (std + 1e-8), metadata


def raw_tabular_metadata():
    return {'schema': SCHEMA_VERSION, 'kind': 'none', 'feature_names': [], 'label_column': None}
