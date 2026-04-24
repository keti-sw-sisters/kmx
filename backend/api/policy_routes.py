"""
ODRL 정책 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from policy.odrl_engine import odrl_engine

router = APIRouter()


class CreatePolicyRequest(BaseModel):
    title: str
    target: str
    assigner: str
    permissions: List[dict]
    prohibitions: List[dict] = []
    obligations: List[dict] = []
    assignee: Optional[str] = None
    policy_type: str = "Offer"


class EvaluatePolicyRequest(BaseModel):
    policy_id: str
    requester_did: str
    action: str = "use"
    context: dict = {}


@router.post("/", summary="정책 생성")
async def create_policy(req: CreatePolicyRequest, db: AsyncSession = Depends(get_db)):
    """ODRL 데이터 사용 정책 생성"""
    return await odrl_engine.create_policy(
        db, req.title, req.target, req.assigner,
        req.permissions, req.prohibitions, req.obligations,
        req.assignee, req.policy_type
    )


@router.get("/", summary="정책 목록")
async def list_policies(db: AsyncSession = Depends(get_db)):
    """전체 정책 목록"""
    return await odrl_engine.list_policies(db)


@router.get("/{policy_id}", summary="정책 조회")
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    """정책 상세 조회 (ODRL JSON-LD)"""
    result = await odrl_engine.get_policy(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")
    return result


@router.post("/evaluate", summary="정책 평가")
async def evaluate_policy(req: EvaluatePolicyRequest, db: AsyncSession = Depends(get_db)):
    """요청이 정책에 부합하는지 평가"""
    result = await odrl_engine.evaluate_policy(
        db, req.policy_id, req.requester_did, req.action, req.context
    )
    return {
        "permitted": result.permitted,
        "reason": result.reason,
        "matched_rules": result.matched_rules,
    }