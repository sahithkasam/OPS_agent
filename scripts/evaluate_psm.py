"""Evaluate the IsolationForest detector on the Pooled Server Metrics (PSM) dataset.

Usage (from the project root):
    python scripts/evaluate_psm.py

Expects data/train.csv (normal data only), data/test.csv and data/test_label.csv.
Reports precision, recall, F1, point-adjusted F1, ROC-AUC and PR-AUC.
"""
import os
import sys

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CONTAMINATION = 0.1  # Same value as src/detection/anomaly_model.py


def load_features(path):
    """Load a PSM CSV, dropping the header row and the timestamp column."""
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, 1:]


def load_labels(path):
    return np.genfromtxt(path, delimiter=",", skip_header=1)[:, 1].astype(int)


def point_adjust(pred, labels):
    """If any point inside a true anomaly segment is detected, count the whole segment as detected."""
    adjusted = pred.copy()
    in_segment = False
    start = 0
    for i in range(len(labels) + 1):
        is_anom = i < len(labels) and labels[i] == 1
        if is_anom and not in_segment:
            in_segment, start = True, i
        elif not is_anom and in_segment:
            in_segment = False
            if pred[start:i].any():
                adjusted[start:i] = 1
    return adjusted


def main():
    train = load_features(os.path.join(DATA_DIR, "train.csv"))
    test = load_features(os.path.join(DATA_DIR, "test.csv"))
    labels = load_labels(os.path.join(DATA_DIR, "test_label.csv"))

    # Drop columns that are entirely NaN in train, then fill remaining gaps with the train median
    keep = ~np.isnan(train).all(axis=0)
    train, test = train[:, keep], test[:, keep]
    medians = np.nanmedian(train, axis=0)
    train = np.where(np.isnan(train), medians, train)
    test = np.where(np.isnan(test), medians, test)

    print(f"Train rows: {len(train)}  Test rows: {len(test)}  Features: {train.shape[1]}")
    print(f"Anomaly rate in test labels: {labels.mean():.3f}")

    model = IsolationForest(contamination=CONTAMINATION, random_state=42)
    model.fit(train)

    pred = (model.predict(test) == -1).astype(int)
    # Lower score_samples means more anomalous, so negate it to get an anomaly score
    scores = -model.score_samples(test)

    precision, recall, f1, _ = precision_recall_fscore_support(labels, pred, average="binary", zero_division=0)
    adj_pred = point_adjust(pred, labels)
    adj_p, adj_r, adj_f1, _ = precision_recall_fscore_support(labels, adj_pred, average="binary", zero_division=0)

    print()
    print(f"Precision:          {precision:.4f}")
    print(f"Recall:             {recall:.4f}")
    print(f"F1:                 {f1:.4f}")
    print(f"Point-adjusted P:   {adj_p:.4f}")
    print(f"Point-adjusted R:   {adj_r:.4f}")
    print(f"Point-adjusted F1:  {adj_f1:.4f}")
    print(f"ROC-AUC:            {roc_auc_score(labels, scores):.4f}")
    print(f"PR-AUC:             {average_precision_score(labels, scores):.4f}")


if __name__ == "__main__":
    sys.exit(main())
