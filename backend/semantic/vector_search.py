"""
벡터 검색 모듈
ChromaDB 또는 간단한 코사인 유사도 기반 의미 검색
자연어로 데이터셋 검색 지원
"""

import math
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import DatasetMetadata
import logging

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """
    의미 기반 데이터셋 검색 엔진
    
    실제 운영: ChromaDB + Ollama 임베딩 사용
    현재: TF-IDF 기반 경량 검색 구현
    """

    # 제조 도메인 어휘 사전
    DOMAIN_VOCAB = {
        "예지보전": ["predictive", "maintenance", "failure", "fault", "sensor", "vibration"],
        "품질": ["quality", "defect", "inspection", "yield", "grade"],
        "에너지": ["energy", "power", "kwh", "electricity", "consumption"],
        "생산": ["production", "output", "quantity", "manufacturing"],
        "공정": ["process", "parameter", "optimization", "control"],
        "설비": ["machine", "equipment", "device", "asset"],
        "온도": ["temperature", "thermal", "heat"],
        "압력": ["pressure", "psi", "bar"],
        "진동": ["vibration", "acceleration", "displacement"],
        "수요": ["demand", "forecast", "order", "sales"],
    }

    def _tokenize(self, text: str) -> list:
        """텍스트 토크나이징"""
        text = text.lower()
        # 한국어 + 영어 분리
        tokens = re.findall(r'[가-힣]+|[a-zA-Z]+', text)
        return tokens

    def _expand_query(self, query: str) -> list:
        """쿼리 확장 (동의어/관련어)"""
        tokens = self._tokenize(query)
        expanded = set(tokens)

        for token in tokens:
            for ko_term, en_terms in self.DOMAIN_VOCAB.items():
                if token == ko_term or any(token in et for et in en_terms):
                    expanded.add(ko_term)
                    expanded.update(en_terms)

        return list(expanded)

    def _compute_score(self, query_tokens: list, dataset: DatasetMetadata) -> float:
        """데이터셋과 쿼리의 유사도 점수 계산"""
        score = 0.0

        # 검색 대상 텍스트 수집
        searchable = []
        searchable.extend(self._tokenize(dataset.title or ""))
        searchable.extend(self._tokenize(dataset.description or ""))
        if dataset.keywords:
            for kw in dataset.keywords:
                searchable.extend(self._tokenize(str(kw)))
        if dataset.columns:
            for col in dataset.columns:
                col_name = col.get("name", "") if isinstance(col, dict) else str(col)
                searchable.extend(self._tokenize(col_name))
                # 온톨로지 매핑된 개념도 검색
                if isinstance(col, dict) and col.get("keywords"):
                    searchable.extend([str(k) for k in col["keywords"]])

        searchable_set = set(searchable)

        for token in query_tokens:
            if token in searchable_set:
                score += 1.0
            # 부분 매칭
            elif any(token in s for s in searchable_set):
                score += 0.5

        # 제목 가중치
        title_tokens = set(self._tokenize(dataset.title or ""))
        for token in query_tokens:
            if token in title_tokens:
                score += 0.5

        return score

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list:
        """
        자연어 쿼리로 데이터셋 검색
        
        Args:
            query: 자연어 검색어 (예: "온도 진동 설비 고장 예측")
            top_k: 반환할 최대 결과 수
            min_score: 최소 유사도 점수
        """
        # 쿼리 확장
        expanded_tokens = self._expand_query(query)
        logger.info(f"검색 쿼리: '{query}' → 확장 토큰: {expanded_tokens[:10]}")

        # 전체 데이터셋 로드
        result = await db.execute(select(DatasetMetadata))
        datasets = result.scalars().all()

        if not datasets:
            return []

        # 유사도 점수 계산
        scored = []
        for dataset in datasets:
            score = self._compute_score(expanded_tokens, dataset)
            if score >= min_score:
                scored.append((score, dataset))

        # 점수 내림차순 정렬
        scored.sort(key=lambda x: x[0], reverse=True)

        # 결과 포맷팅
        results = []
        for rank, (score, dataset) in enumerate(scored[:top_k]):
            results.append({
                "rank": rank + 1,
                "dataset_id": dataset.dataset_id,
                "title": dataset.title,
                "description": dataset.description,
                "owner_did": dataset.owner_did,
                "format": dataset.format,
                "row_count": dataset.row_count,
                "keywords": dataset.keywords,
                "policy_id": dataset.policy_id,
                "relevance_score": round(score, 3),
                "created_at": dataset.created_at.isoformat(),
            })

        logger.info(f"검색 결과: {len(results)}개 (쿼리: '{query}')")
        return results

    async def search_by_ontology(
        self,
        db: AsyncSession,
        concept_uri: str,
        top_k: int = 5,
    ) -> list:
        """온톨로지 개념으로 데이터셋 검색"""
        result = await db.execute(select(DatasetMetadata))
        datasets = result.scalars().all()

        matched = []
        for dataset in datasets:
            if not dataset.ontology_mappings:
                continue
            mappings = dataset.ontology_mappings.get("mappings", {})
            for col, mapping in mappings.items():
                if mapping.get("uri") == concept_uri:
                    matched.append({
                        "dataset_id": dataset.dataset_id,
                        "title": dataset.title,
                        "matched_column": col,
                        "concept_uri": concept_uri,
                        "confidence": mapping.get("confidence", 0.0),
                    })
                    break

        return matched[:top_k]

    def build_embedding(self, text: str) -> list:
        """
        간단한 임베딩 생성 (데모용)
        실제: Ollama/sentence-transformers 사용
        """
        tokens = self._tokenize(text)
        vocab = list(self.DOMAIN_VOCAB.keys()) + [
            t for terms in self.DOMAIN_VOCAB.values() for t in terms
        ]

        vector = [0.0] * len(vocab)
        for i, term in enumerate(vocab):
            if term in tokens:
                vector[i] = 1.0
            elif any(term in t for t in tokens):
                vector[i] = 0.5

        # L2 정규화
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector


# 싱글톤
vector_search = VectorSearchEngine()
