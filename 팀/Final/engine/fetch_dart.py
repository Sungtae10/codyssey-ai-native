"""0단계: OpenDART에서 보고서를 자동으로 받기 (사람이 PDF를 받는 단계를 대신합니다)

사용 예 (engine 폴더에서):
  python fetch_dart.py --companies kakao naver shinhanbank
  python fetch_dart.py --companies skhynix

받은 글: data/dart/<기업>_<보고서키>.txt (저장소에 올리지 않음, 언제든 다시 받을 수 있음)
기록:    data/dart/manifest.json (기업 고유번호, 보고서 이름, 접수번호, DART 원문 주소, 글자 수, 장 찾기 결과)
이후 run.py collect/all은 PDF 대신 이 글을 읽고, 화면의 원문 링크는 DART 원문 주소로 채워집니다.

인증키: 환경 변수 OPENDART_API_KEY 또는 engine/.env (OPENDART_API_KEY=인증키). 인증키는 화면과 기록에 찍지 않습니다.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aipromise import dart  # noqa: E402
from aipromise.config import company_cfg, load_config  # noqa: E402


def fetch(cfg, keys, log=print):
    """기업마다 보고서를 받고 manifest를 갱신합니다. (받은 기업, 못 받은 기업) 목록을 돌려줍니다."""
    key = dart.api_key()
    manifest = dart.load_manifest(cfg)
    manifest.setdefault("companies", {})
    cache = {}

    def corps():
        if "rows" not in cache:
            log("  OpenDART 기업 목록 받는 중 (하루 1번만 받고 data/dart/_corpcode.zip에 둠)")
            cache["rows"] = dart.load_corp_codes(key, dart.dart_dir(cfg))
            log(f"  기업 목록 {len(cache['rows']):,}곳")
        return cache["rows"]

    ok, failed = [], []
    for k in keys:
        c = company_cfg(cfg, k)
        log(f"\n[0단계 DART 자동 수집] {c['name']} ({k})")
        try:
            entry = dart.fetch_company(key, c, dart.dart_dir(cfg), corps, log=log)
        except dart.DartError as e:
            log(f"  실패: {e}")
            failed.append(k)
            continue
        manifest["companies"][k] = entry
        path = dart.save_manifest(cfg, manifest)
        missing = [r["title"] for r in entry["reports"].values() if not r.get("found")]
        if missing:
            log(f"  못 찾은 보고서: {', '.join(missing)}")
            failed.append(k)
        else:
            ok.append(k)
        log(f"  기록: {path}")
    return ok, failed


def main():
    ap = argparse.ArgumentParser(description="OpenDART에서 보고서 자동 수집")
    ap.add_argument("--companies", nargs="+", required=True, help="config.yaml의 기업 이름 (예: kakao naver shinhanbank)")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = load_config(a.config)
    try:
        ok, failed = fetch(cfg, a.companies)
    except dart.DartError as e:
        print(f"멈춤: {e}")
        sys.exit(1)
    print(f"\n받은 기업 {len(ok)}곳 {ok}, 못 받은 기업 {len(failed)}곳 {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
