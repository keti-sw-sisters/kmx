"""
Clearing House API 라우터
"""

from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from clearinghouse.logger import clearing_logger

router = APIRouter()


@router.get("/logs", summary="전송 로그 조회")
async def get_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """데이터 전송 로그 조회 (최근 N건)"""
    return await clearing_logger.get_logs(db, limit)


@router.get("/verify-chain", summary="해시체인 무결성 검증")
async def verify_chain(db: AsyncSession = Depends(get_db)):
    """
    전체 전송 로그의 해시체인 무결성 검증

    위변조 발생 시 해당 레코드 탐지
    """
    return await clearing_logger.verify_chain(db)


@router.get("/usage-report", summary="사용량 정산 보고서")
async def usage_report(
    provider_did: Optional[str] = None,
    consumer_did: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    데이터 사용량 기반 정산 보고서

    - 전송 건수, 용량 집계
    - 과금 금액 계산 (100 KRW/MB)
    """
    return await clearing_logger.get_usage_report(db, provider_did, consumer_did)
"""
Clearing House API 라우터
"""

from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from clearinghouse.logger import clearing_logger

router = APIRouter()


@router.get("/logs", summary="전송 로그 조회")
async def get_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """데이터 전송 로그 조회 (최근 N건)"""
    return await clearing_logger.get_logs(db, limit)


@router.get("/verify-chain", summary="해시체인 무결성 검증")
async def verify_chain(db: AsyncSession = Depends(get_db)):
    """
    전체 전송 로그의 해시체인 무결성 검증
    
    위변조 발생 시 해당 레코드 탐지
    """
    return await clearing_logger.verify_chain(db)


@router.get("/usage-report", summary="사용량 정산 보고서")
async def usage_report(
    provider_did: Optional[str] = None,
    consumer_did: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    데이터 사용량 기반 정산 보고서
    
    - 전송 건수, 용량 집계
    - 과금 금액 계산 (100 KRW/MB)
    """
    return await clearing_logger.get_usage_report(db, provider_did, consumer_did)