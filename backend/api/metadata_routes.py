"""
메타데이터 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from metadata.extractor import metadata_extractor
from semantic.ontology_mapper import ontology_mapper

router = APIRouter()


class ExtractMetadataRequest(BaseModel):
    data: List[dict]
    filename: str = "dataset.json"
    owner_did: str
    policy_id: Optional[str] = None
    dataset_id: Optional[str] = None


class MapOntologyRequest(BaseModel):
    dataset_id: str
    columns: List[str]


@router.post("/extract", summary="메타데이터 추출 및 저장")
async def extract_metadata(req: ExtractMetadataRequest, db: AsyncSession = Depends(get_db)):
    """JSON 데이터에서 DCAT 메타데이터 자동 추출 및 저장"""
    metadata = metadata_extractor.extract_from_json(req.data, req.filename)
    saved = await metadata_extractor.save_metadata(
        db, metadata, req.owner_did, req.dataset_id, req.policy_id
    )
    return {**metadata, **saved}


@router.get("/", summary="데이터셋 카탈로그")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """등록된 데이터셋 전체 카탈로그"""
    return await metadata_extractor.list_datasets(db)


@router.get("/{dataset_id}", summary="데이터셋 상세")
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """데이터셋 상세 메타데이터"""
    result = await metadata_extractor.get_dataset(db, dataset_id)
    if not result:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다")
    return result


@router.post("/ontology/map", summary="온톨로지 매핑")
async def map_ontology(req: MapOntologyRequest, db: AsyncSession = Depends(get_db)):
    """데이터셋 컬럼을 제조 온톨로지 개념으로 매핑"""
    try:
        return await ontology_mapper.map_and_save(db, req.dataset_id, req.columns)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ontology/concepts", summary="온톨로지 개념 목록")
async def list_concepts():
    """제조 도메인 온톨로지 전체 개념 목록"""
    return {"concepts": ontology_mapper.list_concepts()}


@router.get("/ontology/column/{column_name}", summary="컬럼 매핑")
async def map_column(column_name: str):
    """단일 컬럼명의 온톨로지 매핑 조회"""
    return ontology_mapper.map_column(column_name)
"""
메타데이터 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from metadata.extractor import metadata_extractor
from semantic.ontology_mapper import ontology_mapper

router = APIRouter()


class ExtractMetadataRequest(BaseModel):
    data: List[dict]
    filename: str = "dataset.json"
    owner_did: str
    policy_id: Optional[str] = None
    dataset_id: Optional[str] = None


class MapOntologyRequest(BaseModel):
    dataset_id: str
    columns: List[str]


@router.post("/extract", summary="메타데이터 추출 및 저장")
async def extract_metadata(req: ExtractMetadataRequest, db: AsyncSession = Depends(get_db)):
    """JSON 데이터에서 DCAT 메타데이터 자동 추출 및 저장"""
    metadata = metadata_extractor.extract_from_json(req.data, req.filename)
    saved = await metadata_extractor.save_metadata(
        db, metadata, req.owner_did, req.dataset_id, req.policy_id
    )
    return {**metadata, **saved}


@router.get("/", summary="데이터셋 카탈로그")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """등록된 데이터셋 전체 카탈로그"""
    return await metadata_extractor.list_datasets(db)


@router.get("/{dataset_id}", summary="데이터셋 상세")
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """데이터셋 상세 메타데이터"""
    result = await metadata_extractor.get_dataset(db, dataset_id)
    if not result:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다")
    return result


@router.post("/ontology/map", summary="온톨로지 매핑")
async def map_ontology(req: MapOntologyRequest, db: AsyncSession = Depends(get_db)):
    """데이터셋 컬럼을 제조 온톨로지 개념으로 매핑"""
    try:
        return await ontology_mapper.map_and_save(db, req.dataset_id, req.columns)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ontology/concepts", summary="온톨로지 개념 목록")
async def list_concepts():
    """제조 도메인 온톨로지 전체 개념 목록"""
    return {"concepts": ontology_mapper.list_concepts()}


@router.get("/ontology/column/{column_name}", summary="컬럼 매핑")
async def map_column(column_name: str):
    """단일 컬럼명의 온톨로지 매핑 조회"""
    return ontology_mapper.map_column(column_name)