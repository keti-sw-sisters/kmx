"""
계약 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from contract.contract_manager import contract_manager

router = APIRouter()


class CreateContractRequest(BaseModel):
    provider_did: str
    consumer_did: str
    dataset_id: str
    policy_id: str
    valid_days: int = 30
    terms: dict = {}


class SignContractRequest(BaseModel):
    signer_did: str


@router.post("/", summary="계약 생성")
async def create_contract(req: CreateContractRequest, db: AsyncSession = Depends(get_db)):
    """데이터 사용 계약 생성"""
    try:
        return await contract_manager.create_contract(
            db, req.provider_did, req.consumer_did,
            req.dataset_id, req.policy_id, req.valid_days, req.terms
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/sign", summary="계약 서명")
async def sign_contract(
    contract_id: str,
    req: SignContractRequest,
    db: AsyncSession = Depends(get_db)
):
    """계약에 서명 (제공자 또는 소비자)"""
    try:
        return await contract_manager.sign_contract(db, contract_id, req.signer_did)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{contract_id}/verify", summary="계약 검증")
async def verify_contract(
    contract_id: str,
    requester_did: str,
    db: AsyncSession = Depends(get_db)
):
    """계약 유효성 검증"""
    return await contract_manager.verify_contract(db, contract_id, requester_did)


@router.delete("/{contract_id}", summary="계약 종료")
async def terminate_contract(contract_id: str, db: AsyncSession = Depends(get_db)):
    """계약 종료"""
    success = await contract_manager.terminate_contract(db, contract_id)
    if not success:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다")
    return {"message": "계약이 종료되었습니다", "contract_id": contract_id}


@router.get("/", summary="계약 목록")
async def list_contracts(
    did: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """계약 목록 조회"""
    return await contract_manager.list_contracts(db, did)
"""
계약 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from contract.contract_manager import contract_manager

router = APIRouter()


class CreateContractRequest(BaseModel):
    provider_did: str
    consumer_did: str
    dataset_id: str
    policy_id: str
    valid_days: int = 30
    terms: dict = {}


class SignContractRequest(BaseModel):
    signer_did: str


@router.post("/", summary="계약 생성")
async def create_contract(req: CreateContractRequest, db: AsyncSession = Depends(get_db)):
    """데이터 사용 계약 생성"""
    try:
        return await contract_manager.create_contract(
            db, req.provider_did, req.consumer_did,
            req.dataset_id, req.policy_id, req.valid_days, req.terms
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/sign", summary="계약 서명")
async def sign_contract(
    contract_id: str,
    req: SignContractRequest,
    db: AsyncSession = Depends(get_db)
):
    """계약에 서명 (제공자 또는 소비자)"""
    try:
        return await contract_manager.sign_contract(db, contract_id, req.signer_did)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{contract_id}/verify", summary="계약 검증")
async def verify_contract(
    contract_id: str,
    requester_did: str,
    db: AsyncSession = Depends(get_db)
):
    """계약 유효성 검증"""
    return await contract_manager.verify_contract(db, contract_id, requester_did)


@router.delete("/{contract_id}", summary="계약 종료")
async def terminate_contract(contract_id: str, db: AsyncSession = Depends(get_db)):
    """계약 종료"""
    success = await contract_manager.terminate_contract(db, contract_id)
    if not success:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다")
    return {"message": "계약이 종료되었습니다", "contract_id": contract_id}


@router.get("/", summary="계약 목록")
async def list_contracts(
    did: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """계약 목록 조회"""
    return await contract_manager.list_contracts(db, did)