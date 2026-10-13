"""Inter-annotator agreement on the held-out set.

    py -m eval.agreement eval/heldout/labels-human.txt eval/heldout/labels-gpt.txt

Each file has one "<id> <label>" per line. Prints percent agreement,
Cohen's kappa and the disagreements to review.
"""
import sys
from collections import Counter

LABELS = ("included", "extra", "ambiguous")


def read_labels(path: str) -> dict:
    labels = {}
    for line in open(path, encoding="utf-8"):
        parts = line.split()
        if len(parts) >= 2 and parts[1].lower() in LABELS:
            labels[parts[0]] = parts[1].lower()
    return labels


def cohen_kappa(a: list, b: list) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[label] * cb[label] for label in LABELS) / (n * n)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def main():
    first, second = read_labels(sys.argv[1]), read_labels(sys.argv[2])
    ids = sorted(set(first) & set(second))
    missing = sorted(set(first) ^ set(second))
    if missing:
        print(f"Labelled by only one annotator: {', '.join(missing)}")

    a, b = [first[i] for i in ids], [second[i] for i in ids]
    agree = sum(x == y for x, y in zip(a, b))
    print(f"Agreement: {agree}/{len(ids)} ({agree / len(ids):.0%})")
    print(f"Cohen's kappa: {cohen_kappa(a, b):.2f}")
    for label in LABELS:
        print(f"  {label:<10} annotator 1: {a.count(label):>2}   annotator 2: {b.count(label):>2}")

    disagreements = [(i, first[i], second[i]) for i in ids if first[i] != second[i]]
    if disagreements:
        print("\nTo review:")
        for i, x, y in disagreements:
            print(f"  {i:<6} {x:<10} vs {y}")


if __name__ == "__main__":
    main()
