"""
벡터 검색 API 라우터
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from semantic.vector_search import vector_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.1


class OntologySearchRequest(BaseModel):
    concept_uri: str
    top_k: int = 5


@router.post("/datasets", summary="자연어 데이터셋 검색")
async def search_datasets(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    자연어로 데이터셋 의미 검색

    예시: "온도 진동 설비 고장 예측 데이터"
    """
    results = await vector_search.search(db, req.query, req.top_k, req.min_score)
    return {
        "query": req.query,
        "total": len(results),
        "results": results,
    }


@router.get("/datasets", summary="키워드 검색")
async def search_by_keyword(
    q: str,
    top_k: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """URL 파라미터 기반 데이터셋 검색"""
    results = await vector_search.search(db, q, top_k)
    return {"query": q, "total": len(results), "results": results}


@router.post("/ontology", summary="온톨로지 개념 검색")
async def search_by_ontology(req: OntologySearchRequest, db: AsyncSession = Depends(get_db)):
    """온톨로지 URI로 데이터셋 검색"""
    results = await vector_search.search_by_ontology(db, req.concept_uri, req.top_k)
    return {
        "concept_uri": req.concept_uri,
        "total": len(results),
        "results": results,
    }
"""
벡터 검색 API 라우터
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from semantic.vector_search import vector_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.1


class OntologySearchRequest(BaseModel):
    concept_uri: str
    top_k: int = 5


@router.post("/datasets", summary="자연어 데이터셋 검색")
async def search_datasets(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    자연어로 데이터셋 의미 검색
    
    예시: "온도 진동 설비 고장 예측 데이터"
    """
    results = await vector_search.search(db, req.query, req.top_k, req.min_score)
    return {
        "query": req.query,
        "total": len(results),
        "results": results,
    }


@router.get("/datasets", summary="키워드 검색")
async def search_by_keyword(
    q: str,
    top_k: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """URL 파라미터 기반 데이터셋 검색"""
    results = await vector_search.search(db, q, top_k)
    return {"query": q, "total": len(results), "results": results}


@router.post("/ontology", summary="온톨로지 개념 검색")
async def search_by_ontology(req: OntologySearchRequest, db: AsyncSession = Depends(get_db)):
    """온톨로지 URI로 데이터셋 검색"""
    results = await vector_search.search_by_ontology(db, req.concept_uri, req.top_k)
    return {
        "concept_uri": req.concept_uri,
        "total": len(results),
        "results": results,
    }