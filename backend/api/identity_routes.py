"""
Identity API 라우터
DID / VC 관련 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from identity.did import did_manager
from identity.vc import vc_manager

router = APIRouter()


class CreateDIDRequest(BaseModel):
    controller: str
    entity_type: str = "human"  # human | agent | connector


class IssueVCRequest(BaseModel):
    issuer_did: str
    subject_did: str
    vc_type: str
    claims: dict
    valid_days: int = 365


class DelegationRequest(BaseModel):
    human_did: str
    agent_did: str
    permissions: List[str] = ["metadata:create", "catalog:register"]
    valid_hours: int = 24


@router.post("/did", summary="DID 생성")
async def create_did(req: CreateDIDRequest, db: AsyncSession = Depends(get_db)):
    """
    새로운 DID(탈중앙 신원) 생성

    - **controller**: DID 소유자 이름
    - **entity_type**: human | agent | connector
    """
    result = await did_manager.create_did(db, req.controller, req.entity_type)
    return result


@router.get("/did/{did}", summary="DID 조회")
async def resolve_did(did: str, db: AsyncSession = Depends(get_db)):
    """DID 조회 (DID Resolution)"""
    result = await did_manager.resolve_did(db, did)
    if not result:
        raise HTTPException(status_code=404, detail="DID를 찾을 수 없습니다")
    return result


@router.get("/did", summary="DID 목록")
async def list_dids(db: AsyncSession = Depends(get_db)):
    """등록된 DID 목록 조회"""
    return await did_manager.list_dids(db)


@router.post("/vc", summary="VC 발급")
async def issue_vc(req: IssueVCRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifiable Credential 발급

    - **vc_type**: MembershipVC | ManufacturerVC | DelegationVC | DataAccessVC
    """
    try:
        result = await vc_manager.issue_vc(
            db, req.issuer_did, req.subject_did, req.vc_type, req.claims, req.valid_days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vc/{vc_id}/verify", summary="VC 검증")
async def verify_vc(vc_id: str, db: AsyncSession = Depends(get_db)):
    """VC 유효성 검증"""
    return await vc_manager.verify_vc(db, vc_id)


@router.get("/vc", summary="VC 목록")
async def list_vcs(subject_did: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """VC 목록 조회"""
    return await vc_manager.list_vcs(db, subject_did)


@router.post("/vc/delegate", summary="에이전트 위임 VC 발급")
async def issue_delegation(req: DelegationRequest, db: AsyncSession = Depends(get_db)):
    """사용자 → AI 에이전트 권한 위임 VC 발급"""
    try:
        return await vc_manager.issue_delegation_vc(
            db, req.human_did, req.agent_did, req.permissions, req.valid_hours
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/vc/{vc_id}", summary="VC 폐지")
async def revoke_vc(vc_id: str, db: AsyncSession = Depends(get_db)):
    """VC 폐지"""
    success = await vc_manager.revoke_vc(db, vc_id)
    if not success:
        raise HTTPException(status_code=404, detail="VC를 찾을 수 없습니다")
    return {"message": "VC가 폐지되었습니다", "vc_id": vc_id}
"""
Identity API 라우터
DID / VC 관련 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from identity.did import did_manager
from identity.vc import vc_manager

router = APIRouter()


class CreateDIDRequest(BaseModel):
    controller: str
    entity_type: str = "human"  # human | agent | connector


class IssueVCRequest(BaseModel):
    issuer_did: str
    subject_did: str
    vc_type: str
    claims: dict
    valid_days: int = 365


class DelegationRequest(BaseModel):
    human_did: str
    agent_did: str
    permissions: List[str] = ["metadata:create", "catalog:register"]
    valid_hours: int = 24


@router.post("/did", summary="DID 생성")
async def create_did(req: CreateDIDRequest, db: AsyncSession = Depends(get_db)):
    """
    새로운 DID(탈중앙 신원) 생성
    
    - **controller**: DID 소유자 이름
    - **entity_type**: human | agent | connector
    """
    result = await did_manager.create_did(db, req.controller, req.entity_type)
    return result


@router.get("/did/{did}", summary="DID 조회")
async def resolve_did(did: str, db: AsyncSession = Depends(get_db)):
    """DID 조회 (DID Resolution)"""
    result = await did_manager.resolve_did(db, did)
    if not result:
        raise HTTPException(status_code=404, detail="DID를 찾을 수 없습니다")
    return result


@router.get("/did", summary="DID 목록")
async def list_dids(db: AsyncSession = Depends(get_db)):
    """등록된 DID 목록 조회"""
    return await did_manager.list_dids(db)


@router.post("/vc", summary="VC 발급")
async def issue_vc(req: IssueVCRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifiable Credential 발급
    
    - **vc_type**: MembershipVC | ManufacturerVC | DelegationVC | DataAccessVC
    """
    try:
        result = await vc_manager.issue_vc(
            db, req.issuer_did, req.subject_did, req.vc_type, req.claims, req.valid_days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vc/{vc_id}/verify", summary="VC 검증")
async def verify_vc(vc_id: str, db: AsyncSession = Depends(get_db)):
    """VC 유효성 검증"""
    return await vc_manager.verify_vc(db, vc_id)


@router.get("/vc", summary="VC 목록")
async def list_vcs(subject_did: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """VC 목록 조회"""
    return await vc_manager.list_vcs(db, subject_did)


@router.post("/vc/delegate", summary="에이전트 위임 VC 발급")
async def issue_delegation(req: DelegationRequest, db: AsyncSession = Depends(get_db)):
    """사용자 → AI 에이전트 권한 위임 VC 발급"""
    try:
        return await vc_manager.issue_delegation_vc(
            db, req.human_did, req.agent_did, req.permissions, req.valid_hours
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/vc/{vc_id}", summary="VC 폐지")
async def revoke_vc(vc_id: str, db: AsyncSession = Depends(get_db)):
    """VC 폐지"""
    success = await vc_manager.revoke_vc(db, vc_id)
    if not success:
        raise HTTPException(status_code=404, detail="VC를 찾을 수 없습니다")
    return {"message": "VC가 폐지되었습니다", "vc_id": vc_id}