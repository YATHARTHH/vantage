import json
from pathlib import Path
import pytest
from vantage.security.jailbreak_detector import JailbreakDetector

def test_security_detector_benchmark():
    detector = JailbreakDetector()
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "security"
    
    positives = json.loads((fixtures_dir / "positive.json").read_text())
    benign = json.loads((fixtures_dir / "benign.json").read_text())

    tp = 0
    fn = 0
    fp = 0
    tn = 0

    # 1. Test Positive Adversarial Prompts
    for item in positives:
        res = detector.scan_text(item["prompt"])
        if res.is_threat == item["expected_threat"]:
            tp += 1
        else:
            fn += 1

    # 2. Test Benign Prompts
    for item in benign:
        res = detector.scan_text(item["prompt"])
        if res.is_threat == item["expected_threat"]:
            tn += 1
        else:
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    print(f"\n--- SECURITY BENCHMARK METRICS ---")
    print(f"True Positives: {tp}, False Negatives: {fn}")
    print(f"True Negatives: {tn}, False Positives: {fp}")
    print(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}, FPR: {fpr:.2f}")

    assert recall >= 0.80, f"Expected Recall >= 0.80, got {recall:.2f}"
    assert fpr <= 0.05, f"Expected False Positive Rate <= 0.05, got {fpr:.2f}"
