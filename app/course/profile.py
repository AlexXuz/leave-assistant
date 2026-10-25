"""Branch-specific study metadata; never inferred from runnable examples."""
import json
from app.paths import PROJECT_ROOT


def read_profile():
    path=PROJECT_ROOT/'course/profile.json'
    return json.loads(path.read_text(encoding='utf-8'))
