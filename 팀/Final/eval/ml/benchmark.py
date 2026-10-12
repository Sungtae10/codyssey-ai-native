"""PROMISE/EVIDENCE/OTHER baseline: TF-IDF + Logistic Regression."""
import argparse
import csv
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

LABELS = ["PROMISE", "EVIDENCE", "OTHER"]


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r.get("text", "").strip() and r.get("label", "").strip() in LABELS]
    if not rows:
        raise SystemExit("유효한 라벨 데이터가 없습니다.")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out", default="eval/ml/results.json")
    a = ap.parse_args()

    rows = load_rows(a.csv)
    x = [r["text"] for r in rows]
    y = [r["label"] for r in rows]

    counts = {lab: y.count(lab) for lab in LABELS}
    min_class = min(counts.values())
    folds = min(a.folds, min_class)
    if folds < 2:
        raise SystemExit(f"각 클래스에 최소 2개가 필요합니다: {counts}")

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
    ])
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    pred = cross_val_predict(model, x, y, cv=cv)

    result = {
        "n": len(rows),
        "folds": folds,
        "class_counts": counts,
        "accuracy": accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, labels=LABELS, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y, pred, labels=LABELS).tolist(),
        "classification_report": classification_report(
            y, pred, labels=LABELS, output_dict=True, zero_division=0
        ),
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"N={result['n']} / {folds}-fold")
    print(f"Accuracy={result['accuracy']:.3f}")
    print(f"Macro-F1={result['macro_f1']:.3f}")
    print("Confusion matrix labels:", LABELS)
    for row in result["confusion_matrix"]:
        print(row)
    print("저장:", out)


if __name__ == "__main__":
    main()
