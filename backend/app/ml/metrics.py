"""
ML evaluation metrics for CubeSat smoke detection.

Provides comprehensive metric calculations for model evaluation
including accuracy, precision, recall, F1, confusion matrix, PR-AUC,
threshold analysis, and error analysis. Uses numpy only (no sklearn)
for lightweight deployment evaluation scripts.
"""

from __future__ import annotations

from typing import List, Optional, Union

import numpy as np


class MLMetrics:
    """ML evaluation metrics."""

    def __init__(self, class_names: Optional[List[str]] = None) -> None:
        self.class_names = class_names or ["non_smoke", "smoke"]

    def calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
    ) -> dict:
        """Calculate comprehensive metrics.

        Args:
            y_true: Ground truth labels (0 or 1).
            y_pred: Predicted labels (0 or 1).
            y_prob: Predicted probabilities for positive class.

        Returns:
            Dict with accuracy, precision, recall, f1, fpr, fnr,
            confusion_matrix, pr_auc, class_metrics.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)

        cm = self.confusion_matrix(y_true, y_pred)
        accuracy = float(np.mean(y_true == y_pred))

        # Per-class metrics
        class_metrics = {}
        for idx, name in enumerate(self.class_names):
            tp = cm[f"{name}_tp"]
            fp = cm[f"{name}_fp"]
            tn = cm[f"{name}_tn"]
            fn = cm[f"{name}_fn"]

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            class_metrics[name] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": int(tp + fn),
            }

        # Binary metrics (positive class = last class)
        tp = cm[f"{self.class_names[-1]}_tp"]
        fp = cm[f"{self.class_names[-1]}_fp"]
        tn = cm[f"{self.class_names[-1]}_tn"]
        fn = cm[f"{self.class_names[-1]}_fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        pr_auc = self.pr_auc(y_true, y_prob)

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
            "confusion_matrix": cm,
            "pr_auc": round(pr_auc, 4),
            "class_metrics": class_metrics,
        }

    def confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """Compute confusion matrix.

        Returns:
            Dict with tp, fp, tn, fn per class.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)

        if len(self.class_names) == 2:
            # Binary: class_names[0]=negative, class_names[1]=positive
            pos_idx = 1
            neg_idx = 0

            tp = int(np.sum((y_true == pos_idx) & (y_pred == pos_idx)))
            fp = int(np.sum((y_true == neg_idx) & (y_pred == pos_idx)))
            tn = int(np.sum((y_true == neg_idx) & (y_pred == neg_idx)))
            fn = int(np.sum((y_true == pos_idx) & (y_pred == neg_idx)))

            return {
                f"{self.class_names[1]}_tp": tp,
                f"{self.class_names[1]}_fp": fp,
                f"{self.class_names[1]}_tn": tn,
                f"{self.class_names[1]}_fn": fn,
                f"{self.class_names[0]}_tp": tn,
                f"{self.class_names[0]}_fp": fn,
                f"{self.class_names[0]}_tn": tp,
                f"{self.class_names[0]}_fn": fp,
            }

        # Multi-class
        n_classes = len(self.class_names)
        matrix = {}
        for i, name in enumerate(self.class_names):
            tp = int(np.sum((y_true == i) & (y_pred == i)))
            fp = int(np.sum((y_true != i) & (y_pred == i)))
            fn = int(np.sum((y_true == i) & (y_pred != i)))
            tn = int(np.sum((y_true != i) & (y_pred != i)))
            matrix[f"{name}_tp"] = tp
            matrix[f"{name}_fp"] = fp
            matrix[f"{name}_tn"] = tn
            matrix[f"{name}_fn"] = fn

        return matrix

    def classification_report(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
    ) -> str:
        """Generate text classification report."""
        metrics = self.calculate_metrics(y_true, y_pred, y_prob)

        lines = ["              precision  recall  f1-score  support"]
        lines.append("")

        for name in self.class_names:
            cm = metrics["class_metrics"][name]
            lines.append(
                f"  {name:<12s}  {cm['precision']:.4f}  {cm['recall']:.4f}  "
                f"{cm['f1']:.4f}  {cm['support']}"
            )

        lines.append("")
        lines.append(f"  accuracy       {metrics['accuracy']:.4f}")
        lines.append(f"  macro avg      {metrics['precision']:.4f}  {metrics['recall']:.4f}  {metrics['f1']:.4f}")
        lines.append(f"  PR-AUC         {metrics['pr_auc']:.4f}")
        lines.append(f"  FPR            {metrics['fpr']:.4f}")
        lines.append(f"  FNR            {metrics['fnr']:.4f}")

        return "\n".join(lines)

    def pr_auc(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        """Calculate precision-recall AUC using numpy only.

        Computes area under the PR curve by sorting thresholds.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)

        # Sort by probability descending
        sorted_indices = np.argsort(-y_prob)
        y_true_sorted = y_true[sorted_indices]

        total_positives = np.sum(y_true)
        if total_positives == 0:
            return 0.0

        tp_cumsum = np.cumsum(y_true_sorted)
        fp_cumsum = np.cumsum(1 - y_true_sorted)

        precisions = tp_cumsum / (tp_cumsum + fp_cumsum)
        recalls = tp_cumsum / total_positives

        # Add endpoints
        recalls = np.concatenate([[0.0], recalls])
        precisions = np.concatenate([[1.0], precisions])

        # Trapezoidal integration (np.trapezoid in NumPy 2.0+, np.trapz in older)
        _trapz = getattr(np, "trapezoid", None) or np.trapz
        pr_auc_value = float(_trapz(precisions, recalls))
        return max(0.0, min(1.0, pr_auc_value))

    def threshold_analysis(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        thresholds: Optional[List[float]] = None,
    ) -> list:
        """Analyze metrics at different thresholds.

        Returns:
            List of dicts with threshold, precision, recall, f1, fpr.
        """
        if thresholds is None:
            thresholds = np.arange(0.05, 1.0, 0.05).tolist()

        y_true = np.asarray(y_true, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)

        results = []
        for thresh in thresholds:
            y_pred = (y_prob >= thresh).astype(int)

            tp = int(np.sum((y_true == 1) & (y_pred == 1)))
            fp = int(np.sum((y_true == 0) & (y_pred == 1)))
            tn = int(np.sum((y_true == 0) & (y_pred == 0)))
            fn = int(np.sum((y_true == 1) & (y_pred == 0)))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            results.append({
                "threshold": round(float(thresh), 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "fpr": round(fpr, 4),
            })

        return results

    def error_analysis(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
        image_ids: Optional[List[str]] = None,
    ) -> dict:
        """Identify false positives/negatives with details.

        Returns:
            Dict with false_positives, false_negatives, hard_negatives lists.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)

        if image_ids is None:
            image_ids = [f"sample_{i}" for i in range(len(y_true))]

        false_positives = []
        false_negatives = []
        hard_negatives = []

        for i in range(len(y_true)):
            entry = {
                "index": int(i),
                "image_id": image_ids[i],
                "true_label": int(y_true[i]),
                "predicted_label": int(y_pred[i]),
                "probability": round(float(y_prob[i]), 4),
            }

            if y_true[i] == 0 and y_pred[i] == 1:
                false_positives.append(entry)
                if y_prob[i] > 0.7:
                    hard_negatives.append(entry)
            elif y_true[i] == 1 and y_pred[i] == 0:
                false_negatives.append(entry)

        return {
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "hard_negatives": hard_negatives,
        }
