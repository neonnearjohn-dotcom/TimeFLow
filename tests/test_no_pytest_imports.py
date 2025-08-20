import pathlib


def test_no_pytest_imports_outside_tests():
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if "import pytest" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], f"import pytest outside tests: {offenders}"
