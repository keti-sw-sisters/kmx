"""
Clearing House - 공증 및 정산 모듈
데이터 전송 로그 해시체인 기반 위변조 방지
"""

import uuid
import hashlib
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models import TransferLog
import logging

logger = logging.getLogger(__name__)


class ClearingHouseLogger:
    """
    해시체인 기반 불변 감사 로그
    
    각 로그 레코드는 이전 레코드의 해시를 포함
    → 중간 레코드 변조 시 전체 체인 무효화
    """

    async def _get_last_hash(self, db: AsyncSession) -> Optional[str]:
        """마지막 로그의 해시 조회 (체인 연결용)"""
        result = await db.execute(
            select(TransferLog.current_hash).order_by(
                TransferLog.timestamp.desc()
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        return row

    def _compute_hash(self, data: dict, prev_hash: Optional[str]) -> str:
        """
        로그 레코드 해시 계산
        SHA-256(prev_hash + current_data)
        """
        payload = {
            "prev": prev_hash or "GENESIS",
            **data
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    async def log_transfer(
        self,
        db: AsyncSession,
        transfer_id: str,
        contract_id: str,
        provider_did: str,
        consumer_did: str,
        dataset_id: str,
        bytes_transferred: int,
        status: str = "SUCCESS",
        metadata: dict = None,
    ) -> dict:
        """
        데이터 전송 로그 기록
        이전 로그와 해시체인으로 연결
        """
        prev_hash = await self._get_last_hash(db)

        log_data = {
            "transfer_id": transfer_id,
            "contract_id": contract_id,
            "provider_did": provider_did,
            "consumer_did": consumer_did,
            "dataset_id": dataset_id,
            "bytes_transferred": bytes_transferred,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        current_hash = self._compute_hash(log_data, prev_hash)

        log_record = TransferLog(
            transfer_id=transfer_id,
            contract_id=contract_id,
            provider_did=provider_did,
            consumer_did=consumer_did,
            dataset_id=dataset_id,
            bytes_transferred=bytes_transferred,
            status=status,
            prev_hash=prev_hash,
            current_hash=current_hash,
            metadata=metadata or {},
        )
        db.add(log_record)
        await db.flush()

        logger.info(f"📋 전송 로그 기록: {transfer_id} | hash={current_hash[:16]}...")
        return {
            "transfer_id": transfer_id,
            "current_hash": current_hash,
            "prev_hash": prev_hash,
            "timestamp": log_data["timestamp"],
        }

    async def verify_chain(self, db: AsyncSession) -> dict:
        """
        해시체인 무결성 검증
        모든 로그를 순서대로 재계산하여 위변조 탐지
        """
        result = await db.execute(
            select(TransferLog).order_by(TransferLog.timestamp.asc())
        )
        logs = result.scalars().all()

        if not logs:
            return {"valid": True, "total": 0, "message": "로그 없음"}

        errors = []
        for i, log in enumerate(logs):
            log_data = {
                "transfer_id": log.transfer_id,
                "contract_id": log.contract_id,
                "provider_did": log.provider_did,
                "consumer_did": log.consumer_did,
                "dataset_id": log.dataset_id,
                "bytes_transferred": log.bytes_transferred,
                "status": log.status,
                "timestamp": log.timestamp.isoformat(),
            }
            expected_hash = self._compute_hash(log_data, log.prev_hash)
            if expected_hash != log.current_hash:
                errors.append({
                    "index": i,
                    "transfer_id": log.transfer_id,
                    "expected": expected_hash[:16],
                    "actual": log.current_hash[:16],
                })

        return {
            "valid": len(errors) == 0,
            "total": len(logs),
            "errors": errors,
            "message": "체인 무결성 검증 완료" if not errors else f"{len(errors)}개 레코드 위변조 탐지",
        }

    async def get_usage_report(
        self,
        db: AsyncSession,
        provider_did: Optional[str] = None,
        consumer_did: Optional[str] = None,
    ) -> dict:
        """
        사용량 기반 정산 보고서
        전송 로그 집계
        """
        query = select(TransferLog)
        from sqlalchemy import or_
        filters = []
        if provider_did:
            filters.append(TransferLog.provider_did == provider_did)
        if consumer_did:
            filters.append(TransferLog.consumer_did == consumer_did)
        if filters:
            query = query.where(*filters)

        result = await db.execute(query)
        logs = result.scalars().all()

        total_bytes = sum(l.bytes_transferred for l in logs)
        success_count = sum(1 for l in logs if l.status == "SUCCESS")

        # 정산 계산 (단순화: 1MB당 100원)
        billing_amount = (total_bytes / 1_000_000) * 100

        return {
            "total_transfers": len(logs),
            "success_transfers": success_count,
            "total_bytes_transferred": total_bytes,
            "total_mb": round(total_bytes / 1_000_000, 4),
            "billing_amount_krw": round(billing_amount, 2),
            "billing_unit": "100 KRW/MB",
            "period": {
                "from": logs[0].timestamp.isoformat() if logs else None,
                "to": logs[-1].timestamp.isoformat() if logs else None,
            },
            "breakdown": [
                {
                    "transfer_id": l.transfer_id,
                    "dataset_id": l.dataset_id,
                    "bytes": l.bytes_transferred,
                    "status": l.status,
                    "timestamp": l.timestamp.isoformat(),
                }
                for l in logs[:20]  # 최근 20건
            ]
        }

    async def get_logs(
        self,
        db: AsyncSession,
        limit: int = 50,
    ) -> list:
        """최근 로그 조회"""
        result = await db.execute(
            select(TransferLog).order_by(TransferLog.timestamp.desc()).limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "transfer_id": l.transfer_id,
                "contract_id": l.contract_id,
                "provider_did": l.provider_did,
                "consumer_did": l.consumer_did,
                "dataset_id": l.dataset_id,
                "bytes_transferred": l.bytes_transferred,
                "status": l.status,
                "timestamp": l.timestamp.isoformat(),
                "hash": l.current_hash[:16] + "...",
            }
            for l in logs
        ]


# 싱글톤
clearing_logger = ClearingHouseLogger()
