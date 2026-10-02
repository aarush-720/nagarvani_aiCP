"""Rebuild the classifier artefact deterministically:  python -m nagarvani.train"""
from . import classifier, config
from .console import safe_console


def main():
    safe_console()
    model, meta = classifier.fit()
    classifier.save(model, meta)
    print(f"saved {config.CLASSIFIER_PATH}  C={meta['C']}  CV accuracy on train={meta['cv_accuracy']:.4f}")


if __name__ == "__main__":
    main()
