"""
Agent API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from ai.agent import default_agent

router = APIRouter()


class AutoCatalogRequest(BaseModel):
    data: List[dict]
    dataset_name: str
    owner_did: str
    policy_id: Optional[str] = None


class DelegateRequest(BaseModel):
    human_did: str
    permissions: List[str] = ["metadata:create", "catalog:register", "ontology:map"]


@router.post("/initialize", summary="에이전트 초기화")
async def initialize_agent(db: AsyncSession = Depends(get_db)):
    """에이전트 DID 생성 및 초기화"""
    return await default_agent.initialize(db)


@router.post("/delegate", summary="권한 위임")
async def delegate_to_agent(req: DelegateRequest, db: AsyncSession = Depends(get_db)):
    """사용자 → 에이전트 권한 위임 VC 발급"""
    return await default_agent.receive_delegation(db, req.human_did, req.permissions)


@router.post("/auto-catalog", summary="자동 카탈로그 생성")
async def auto_catalog(req: AutoCatalogRequest, db: AsyncSession = Depends(get_db)):
    """
    AI 에이전트 자동 카탈로그 생성

    수행 작업:
    1. 메타데이터 자동 추출
    2. 온톨로지 매핑
    3. 데이터 플레인 등록
    4. DCAT 카탈로그 저장
    5. API 초안 생성
    """
    if not default_agent.agent_did:
        await default_agent.initialize(db)

    return await default_agent.auto_catalog_dataset(
        db=db,
        data=req.data,
        dataset_name=req.dataset_name,
        owner_did=req.owner_did,
        policy_id=req.policy_id,
    )


@router.get("/health", summary="에이전트 상태")
async def agent_health():
    """에이전트 상태 확인"""
    return await default_agent.run_health_check()
"""
Agent API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from ai.agent import default_agent

router = APIRouter()


class AutoCatalogRequest(BaseModel):
    data: List[dict]
    dataset_name: str
    owner_did: str
    policy_id: Optional[str] = None


class DelegateRequest(BaseModel):
    human_did: str
    permissions: List[str] = ["metadata:create", "catalog:register", "ontology:map"]


@router.post("/initialize", summary="에이전트 초기화")
async def initialize_agent(db: AsyncSession = Depends(get_db)):
    """에이전트 DID 생성 및 초기화"""
    return await default_agent.initialize(db)


@router.post("/delegate", summary="권한 위임")
async def delegate_to_agent(req: DelegateRequest, db: AsyncSession = Depends(get_db)):
    """사용자 → 에이전트 권한 위임 VC 발급"""
    return await default_agent.receive_delegation(db, req.human_did, req.permissions)


@router.post("/auto-catalog", summary="자동 카탈로그 생성")
async def auto_catalog(req: AutoCatalogRequest, db: AsyncSession = Depends(get_db)):
    """
    AI 에이전트 자동 카탈로그 생성
    
    수행 작업:
    1. 메타데이터 자동 추출
    2. 온톨로지 매핑
    3. 데이터 플레인 등록
    4. DCAT 카탈로그 저장
    5. API 초안 생성
    """
    if not default_agent.agent_did:
        await default_agent.initialize(db)

    return await default_agent.auto_catalog_dataset(
        db=db,
        data=req.data,
        dataset_name=req.dataset_name,
        owner_did=req.owner_did,
        policy_id=req.policy_id,
    )


@router.get("/health", summary="에이전트 상태")
async def agent_health():
    """에이전트 상태 확인"""
    return await default_agent.run_health_check()