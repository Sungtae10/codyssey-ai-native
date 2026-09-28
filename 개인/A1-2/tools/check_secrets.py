#!/usr/bin/env python3
"""커밋 전에 실행하는 키 노출 검사.

.env에 적힌 실제 키 값(과 대표적인 키 모양)이 프로젝트 파일 어디에도 들어 있지 않은지 확인한다.
코드, README, results/ 결과 파일, 로그 파일까지 모두 검사한다(.env 자체와 .venv는 제외).

사용법 : python tools/check_secrets.py
종료 코드: 0 = 문제 없음, 1 = 키가 발견됨 (파일:줄 번호와 키 이름만 보여 주고 값은 보여 주지 않음)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".idea", ".vscode"}
SECRET_NAME = re.compile(r"(KEY|SECRET|TOKEN|CLIENT_ID)$")
KEY_SHAPES = [
    ("OpenAI 키 모양(sk-...)", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("Google API 키 모양(AIza...)", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
]


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8")


def env_secrets(path: Path) -> dict[str, str]:
    """ .env에서 이름이 KEY/SECRET/TOKEN/CLIENT_ID로 끝나는 값만 모은다."""
    secrets: dict[str, str] = {}
    if not path.is_file():
        return secrets
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if SECRET_NAME.search(name) and len(value) >= 8:
            secrets[name] = value
    return secrets


def project_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            continue  # .env와 .env.bak 같은 비밀 파일 자체는 검사 대상이 아님(Git에 안 올라감)
        yield path


def env_tracked_by_git() -> bool | None:
    """.env가 Git에 올라가 있으면 True, 아니면 False, Git을 못 쓰면 None."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if "not a git repository" in (result.stderr or "").lower():
        return None
    return result.returncode == 0


def main() -> int:
    secrets = env_secrets(ROOT / ".env")
    findings: list[tuple[str, int, str]] = []
    checked = 0
    for path in project_files():
        try:
            text = _read_text(path)
        except (UnicodeDecodeError, OSError):
            continue  # 이미지 같은 이진 파일은 건너뜀
        checked += 1
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(text.splitlines(), start=1):
            for name, value in secrets.items():
                if value in line:
                    findings.append((rel, number, f"{name} 값"))
            for label, pattern in KEY_SHAPES:
                if pattern.search(line):
                    findings.append((rel, number, label))

    print(f"[키 노출 검사] 텍스트 파일 {checked}개 검사, .env에서 읽은 키 {len(secrets)}개")
    if not secrets:
        print("  (참고: .env가 없거나 비어 있어 키 모양 패턴만 검사했습니다)")
    ok = True
    if findings:
        ok = False
        print("  [위험] 아래 위치에서 키가 발견됐습니다. 지우고 다시 검사하세요. 이미 올렸다면 키를 폐기 후 재발급하세요.")
        for rel, number, label in findings:
            print(f"    - {rel}:{number}  ({label})")
    else:
        print("  OK: 키 값이 들어 있는 파일이 없습니다.")

    tracked = env_tracked_by_git()
    if tracked is True:
        ok = False
        print("  [위험] .env가 Git에 올라가 있습니다. 실행: git rm --cached .env  (그리고 키 재발급)")
    elif tracked is False:
        print("  OK: .env는 Git 추적 대상이 아닙니다.")
    else:
        print("  (참고: Git 저장소가 아니어서 .env 추적 여부는 건너뛰었습니다)")
    print("  참고: 스크린샷(이미지) 속 글자는 검사하지 못합니다. 캡처에 키가 찍히지 않았는지 눈으로 확인하세요.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
