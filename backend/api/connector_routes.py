"""
Connector API 라우터
EDC Control Plane / Data Plane 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from connector.control_plane import control_plane
from connector.data_plane import data_plane

router = APIRouter()


class RegisterConnectorRequest(BaseModel):
    name: str
    owner_did: str
    endpoint_url: str
    capabilities: List[str] = ["data-transfer", "contract-negotiation"]
    trust_level: str = "STANDARD"


class NegotiationRequest(BaseModel):
    consumer_did: str
    provider_connector_id: str
    dataset_id: str
    policy_id: str
    consumer_vc_id: Optional[str] = None


class DataTransferRequest(BaseModel):
    contract_id: str
    dataset_id: str
    requester_did: str
    format: str = "json"


class RegisterDatasetRequest(BaseModel):
    dataset_id: str
    data: List[dict]
    owner_did: str


class RouteRequest(BaseModel):
    target_connector_id: str
    payload: dict


# ──── Control Plane ────

@router.post("/register", summary="커넥터 등록")
async def register_connector(req: RegisterConnectorRequest, db: AsyncSession = Depends(get_db)):
    """EDC 커넥터를 레지스트리에 등록"""
    return await control_plane.register_connector(
        db, req.name, req.owner_did, req.endpoint_url, req.capabilities, req.trust_level
    )


@router.get("/list", summary="커넥터 목록")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    """등록된 커넥터 목록"""
    return await control_plane.list_connectors(db)


@router.post("/negotiate", summary="계약 협상 시작")
async def initiate_negotiation(req: NegotiationRequest, db: AsyncSession = Depends(get_db)):
    """
    데이터 접근 계약 협상 시작

    IDS-RAM ContractRequestMessage 기반
    """
    result = await control_plane.initiate_contract_negotiation(
        db=db,
        consumer_did=req.consumer_did,
        provider_connector_id=req.provider_connector_id,
        dataset_id=req.dataset_id,
        policy_id=req.policy_id,
        consumer_vc_id=req.consumer_vc_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.post("/validate", summary="데이터 요청 검증")
async def validate_request(
    contract_id: str,
    requester_did: str,
    action: str = "use",
    db: AsyncSession = Depends(get_db)
):
    """Data Plane 접근 전 권한 검증"""
    return await control_plane.validate_data_request(db, contract_id, requester_did, action)


@router.post("/route", summary="연합 커넥터 라우팅")
async def route_request(req: RouteRequest, db: AsyncSession = Depends(get_db)):
    """다른 커넥터로 요청 라우팅"""
    return await control_plane.route_request(db, req.target_connector_id, req.payload)


# ──── Data Plane ────

@router.post("/data/register", summary="데이터셋 등록")
async def register_dataset(req: RegisterDatasetRequest):
    """데이터 플레인에 데이터셋 등록 (제공자 측)"""
    return await data_plane.register_dataset(req.dataset_id, req.data, req.owner_did)


@router.post("/data/transfer", summary="데이터 전송")
async def transfer_data(req: DataTransferRequest, db: AsyncSession = Depends(get_db)):
    """
    계약 기반 데이터 P2P 전송

    흐름: 권한검증 → 데이터로드 → 전송 → 로그기록
    """
    result = await data_plane.transfer_data(
        db=db,
        contract_id=req.contract_id,
        dataset_id=req.dataset_id,
        requester_did=req.requester_did,
        format=req.format,
    )
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.get("/data/{dataset_id}/info", summary="데이터셋 정보")
async def get_dataset_info(dataset_id: str):
    """데이터 플레인 데이터셋 정보"""
    info = await data_plane.get_dataset_info(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다")
    return info
"""
Connector API 라우터
EDC Control Plane / Data Plane 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from connector.control_plane import control_plane
from connector.data_plane import data_plane

router = APIRouter()


class RegisterConnectorRequest(BaseModel):
    name: str
    owner_did: str
    endpoint_url: str
    capabilities: List[str] = ["data-transfer", "contract-negotiation"]
    trust_level: str = "STANDARD"


class NegotiationRequest(BaseModel):
    consumer_did: str
    provider_connector_id: str
    dataset_id: str
    policy_id: str
    consumer_vc_id: Optional[str] = None


class DataTransferRequest(BaseModel):
    contract_id: str
    dataset_id: str
    requester_did: str
    format: str = "json"


class RegisterDatasetRequest(BaseModel):
    dataset_id: str
    data: List[dict]
    owner_did: str


class RouteRequest(BaseModel):
    target_connector_id: str
    payload: dict


# ──── Control Plane ────

@router.post("/register", summary="커넥터 등록")
async def register_connector(req: RegisterConnectorRequest, db: AsyncSession = Depends(get_db)):
    """EDC 커넥터를 레지스트리에 등록"""
    return await control_plane.register_connector(
        db, req.name, req.owner_did, req.endpoint_url, req.capabilities, req.trust_level
    )


@router.get("/list", summary="커넥터 목록")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    """등록된 커넥터 목록"""
    return await control_plane.list_connectors(db)


@router.post("/negotiate", summary="계약 협상 시작")
async def initiate_negotiation(req: NegotiationRequest, db: AsyncSession = Depends(get_db)):
    """
    데이터 접근 계약 협상 시작
    
    IDS-RAM ContractRequestMessage 기반
    """
    result = await control_plane.initiate_contract_negotiation(
        db=db,
        consumer_did=req.consumer_did,
        provider_connector_id=req.provider_connector_id,
        dataset_id=req.dataset_id,
        policy_id=req.policy_id,
        consumer_vc_id=req.consumer_vc_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.post("/validate", summary="데이터 요청 검증")
async def validate_request(
    contract_id: str,
    requester_did: str,
    action: str = "use",
    db: AsyncSession = Depends(get_db)
):
    """Data Plane 접근 전 권한 검증"""
    return await control_plane.validate_data_request(db, contract_id, requester_did, action)


@router.post("/route", summary="연합 커넥터 라우팅")
async def route_request(req: RouteRequest, db: AsyncSession = Depends(get_db)):
    """다른 커넥터로 요청 라우팅"""
    return await control_plane.route_request(db, req.target_connector_id, req.payload)


# ──── Data Plane ────

@router.post("/data/register", summary="데이터셋 등록")
async def register_dataset(req: RegisterDatasetRequest):
    """데이터 플레인에 데이터셋 등록 (제공자 측)"""
    return await data_plane.register_dataset(req.dataset_id, req.data, req.owner_did)


@router.post("/data/transfer", summary="데이터 전송")
async def transfer_data(req: DataTransferRequest, db: AsyncSession = Depends(get_db)):
    """
    계약 기반 데이터 P2P 전송
    
    흐름: 권한검증 → 데이터로드 → 전송 → 로그기록
    """
    result = await data_plane.transfer_data(
        db=db,
        contract_id=req.contract_id,
        dataset_id=req.dataset_id,
        requester_did=req.requester_did,
        format=req.format,
    )
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.get("/data/{dataset_id}/info", summary="데이터셋 정보")
async def get_dataset_info(dataset_id: str):
    """데이터 플레인 데이터셋 정보"""
    info = await data_plane.get_dataset_info(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다")
    return info