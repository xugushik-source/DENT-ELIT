"""Resolve template provenance in a git checkout or verified portable release."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from factory.policy import ROOT


def template_commit(root=ROOT):
    root = Path(root).resolve()
    release = root / "factory-release.json"
    if release.is_file():
        manifest = json.loads(release.read_text(encoding="utf-8"))
        commit = manifest.get("commit", "")
        if not re.fullmatch(r"[a-f0-9]{40}", commit) or not manifest.get("files"):
            raise ValueError("Повреждён паспорт локальной версии")
        for name, expected in manifest["files"].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("Отсутствует файл локальной версии: " + name)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Файл локальной версии изменён: " + name)
        return commit
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            stderr=subprocess.DEVNULL, timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Запустите кабинет из готового архива или git-репозитория") from error
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Не удалось определить версию шаблона")
    return commit
