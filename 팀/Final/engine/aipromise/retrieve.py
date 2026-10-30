"""4단계: 근거 검색 (RAG의 검색 부분).

두 가지 검색을 함께 씁니다.
- 키워드 검색(BM25): 제품명, 공장명처럼 글자가 같은 문장을 잘 찾습니다.
- 의미 검색(OpenAI 임베딩 + ChromaDB): 표현이 달라도 뜻이 비슷한 문장을 찾습니다.
두 결과를 순위 합치기(RRF)로 섞습니다. DART-Foresight AI 평가에서 검색이 약점(Hit@4 14/20)이었기 때문에
의미 검색만 쓰지 않고 키워드 검색을 더했습니다.
"""
import re
import math
import os
from collections import Counter

from .textutil import tokenize


class Corpus:
    """후속 보고서(근거를 찾는 보고서)의 문장 모음."""

    def __init__(self, collected_reports):
        self.sents = []      # [{id, text, page, report, report_key, section_key, section, url}]
        self.by_id = {}
        self.order = {}      # id → (보고서·장 안에서의 순서 목록, 위치)
        for rep in collected_reports:
            for skey, sec in rep["sections"].items():
                ids = []
                for s in sec["sentences"]:
                    item = {
                        "id": s["id"], "text": s["text"], "page": s["page"],
                        "report": rep["title"], "report_key": rep["report_key"],
                        "section_key": skey, "section": sec["name"], "url": rep.get("url", ""),
                    }
                    self.sents.append(item)
                    self.by_id[s["id"]] = item
                    ids.append(s["id"])
                for i, sid in enumerate(ids):
                    self.order[sid] = (ids, i)
        self.windows = [self.window_text(s["id"]) for s in self.sents]

    def neighbors(self, sid, width=1):
        ids, i = self.order[sid]
        return ids[max(0, i - width): i + width + 1]

    def window_text(self, sid):
        return " ".join(self.by_id[x]["text"] for x in self.neighbors(sid))


class KeywordIndex:
    def __init__(self, texts, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query, k=20):
        q = Counter(tokenize(query))
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t not in d:
                    continue
                tf = d[t]
                s += self.idf.get(t, 0) * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.lens[i] / (self.avg or 1)))
            if s > 0:
                scores.append((s, i))
        scores.sort(reverse=True)
        return [i for _, i in scores[:k]]


class VectorIndex:
    """ChromaDB에 문장 창(앞뒤 문장 포함)을 넣어 둡니다. 한 번 만들면 다시 쓰고, 문장 수가 바뀌면 새로 만듭니다."""

    def __init__(self, cfg, company_key, corpus, persist_dir):
        from langchain_chroma import Chroma
        from .llm import get_embeddings
        emb = get_embeddings(cfg)
        # 임베딩 모델마다 벡터 크기가 달라서(small 1536, large 3072) 모델 이름을 DB 이름에 넣습니다
        model_tag = re.sub(r"[^a-z0-9]+", "-", str(cfg["llm"]["embed_model"]).lower()).strip("-")
        name = f"aip_{company_key}_{model_tag}"[:60].rstrip("-_")
        self.db = Chroma(collection_name=name, embedding_function=emb, persist_directory=persist_dir)
        if self.db._collection.count() != len(corpus.sents):
            if self.db._collection.count() > 0:
                self.db.delete_collection()
                self.db = Chroma(collection_name=name, embedding_function=emb, persist_directory=persist_dir)
            batch = 200
            for i in range(0, len(corpus.sents), batch):
                part = corpus.sents[i:i + batch]
                self.db.add_texts(
                    texts=[corpus.windows[i + j] for j in range(len(part))],
                    metadatas=[{"sid": s["id"]} for s in part],
                    ids=[s["id"] for s in part],
                )
        self.index_of = {s["id"]: i for i, s in enumerate(corpus.sents)}

    def search(self, query, k=20):
        docs = self.db.similarity_search(query, k=k)
        return [self.index_of[d.metadata["sid"]] for d in docs if d.metadata.get("sid") in self.index_of]


class HybridRetriever:
    def __init__(self, cfg, company_key, corpus, work_dir, mock=False):
        self.corpus = corpus
        self.kw = KeywordIndex(corpus.windows)
        self.vec = None
        self.mode = "키워드"
        if not mock and cfg["retrieval"].get("use_vector", True):
            self.vec = VectorIndex(cfg, company_key, corpus, os.path.join(work_dir, "chroma_db"))
            self.mode = "키워드 + 의미"
        self.top_windows = cfg["retrieval"].get("top_windows", 8)
        self.max_candidates = cfg["retrieval"].get("max_candidates", 24)

    def search(self, query):
        ranked = {}
        lists = [self.kw.search(query, 20)]
        if self.vec:
            lists.append(self.vec.search(query, 20))
        for lst in lists:
            for rank, idx in enumerate(lst):
                ranked[idx] = ranked.get(idx, 0) + 1.0 / (60 + rank)
        top = sorted(ranked, key=lambda i: -ranked[i])[: self.top_windows]
        out, seen = [], set()
        for idx in top:
            for sid in self.corpus.neighbors(self.corpus.sents[idx]["id"]):
                if sid not in seen:
                    seen.add(sid)
                    out.append(sid)
                if len(out) >= self.max_candidates:
                    return out
        return out
