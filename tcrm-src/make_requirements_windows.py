"""Build requirements.windows.txt from requirements.txt for Win + Python 3.13+."""
from pathlib import Path

root = Path(__file__).resolve().parent
src = (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
out = []
for line in src:
    if "rl-renderPM" in line:
        continue
    s = line.strip()
    if s.startswith("lxml==5.2.1") and "python_version >= '3.12'" in line:
        out.append(
            "lxml>=6.0.2 ; python_version >= '3.12'  # binary wheel; use lxml-html-clean"
        )
        continue
    if s.startswith("psycopg2==2.9.10") and "python_version >= '3.13'" in line:
        out.append(
            "psycopg2-binary>=2.9.10 ; python_version >= '3.13'  # Windows wheels"
        )
        continue
    if s.startswith("Pillow==11.1.0") and "python_version >= '3.13'" in line:
        out.append(
            "Pillow>=12.0.0 ; python_version >= '3.13'  # binary wheels on Win/py3.14"
        )
        continue
    out.append(line)
(root / "requirements.windows.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"Wrote requirements.windows.txt ({len(out)} lines)")
