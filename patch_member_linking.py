from pathlib import Path
from datetime import datetime
import shutil
import sys

root = Path.cwd()
app_path = root / "app.py"
js_path = root / "static" / "app.js"

app = app_path.read_text()
js = js_path.read_text()

# Verify the exact source fragments before making any changes.
checks = [
    ('app.py', '@app.get("/api/users")'),
    ('app.py', '@app.post("/api/users")'),
    ('app.py', '@app.put("/api/users/<int:uid>")'),
    ('static/app.js', 'users:[["username","Username","text"]'),
    ('static/app.js', 'async function openForm()'),
]

for filename, fragment in checks:
    source = app if filename == "app.py" else js
    if fragment not in source:
        print(f"STOP: Expected code not found in {filename}: {fragment}")
        sys.exit(1)

print("Pre-check passed. No files changed.")
print("This is a safety checkpoint; the patch itself has not been applied.")
print("Next we will apply the tested backend and frontend changes.")
