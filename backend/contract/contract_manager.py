#계약 생성/서명/검증
"""
데이터 사용 계약 관리자
EDC Contract Negotiation 프로토콜 기반
"""

import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import DataContract, ODRLPolicy, DID as DIDModel
from identity.did import did_manager
import logging

logger = logging.getLogger(__name__)


class ContractManager:
    """데이터 계약 생성, 협상, 검증"""

    CONTRACT_STATES = ["PENDING", "NEGOTIATING", "ACTIVE", "TERMINATED", "EXPIRED"]

    async def create_contract(
        self,
        db: AsyncSession,
        provider_did: str,
        consumer_did: str,
        dataset_id: str,
        policy_id: str,
        valid_days: int = 30,
        terms: dict = None,
    ) -> dict:
        """
        데이터 계약 생성
        
        계약 흐름:
        1. 소비자가 계약 요청 (PENDING)
        2. 제공자가 수락 → 서명 (NEGOTIATING)
        3. 소비자 서명 → 발효 (ACTIVE)
        """
        # 정책 존재 확인
        pol_result = await db.execute(
            select(ODRLPolicy).where(ODRLPolicy.policy_id == policy_id)
        )
        policy = pol_result.scalar_one_or_none()
        if not policy:
            raise ValueError(f"정책을 찾을 수 없습니다: {policy_id}")

        contract_id = f"contract:kmx:{uuid.uuid4().hex[:16]}"
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=valid_days)

        contract = DataContract(
            contract_id=contract_id,
            provider_did=provider_did,
            consumer_did=consumer_did,
            dataset_id=dataset_id,
            policy_id=policy_id,
            status="PENDING",
            start_date=start_date,
            end_date=end_date,
            terms=terms or {},
        )
        db.add(contract)
        await db.flush()

        logger.info(f"✅ 계약 생성: {contract_id}")
        return self._serialize_contract(contract)

    async def sign_contract(
        self,
        db: AsyncSession,
        contract_id: str,
        signer_did: str,
    ) -> dict:
        """
        계약 서명 (제공자 또는 소비자)
        양측 서명 완료 시 ACTIVE 상태로 전환
        """
        result = await db.execute(
            select(DataContract).where(DataContract.contract_id == contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"계약을 찾을 수 없습니다: {contract_id}")

        # DID 조회 및 서명 생성
        did_result = await db.execute(
            select(DIDModel).where(DIDModel.did == signer_did)
        )
        did_record = did_result.scalar_one_or_none()
        if not did_record:
            raise ValueError(f"서명자 DID를 찾을 수 없습니다: {signer_did}")

        contract_data = {
            "contract_id": contract_id,
            "provider": contract.provider_did,
            "consumer": contract.consumer_did,
            "dataset": contract.dataset_id,
            "policy": contract.policy_id,
        }
        signature = did_manager.sign_data(did_record.private_key_enc, contract_data)

        if signer_did == contract.provider_did:
            contract.provider_signature = signature
            logger.info(f"제공자 서명 완료: {contract_id}")
        elif signer_did == contract.consumer_did:
            contract.consumer_signature = signature
            logger.info(f"소비자 서명 완료: {contract_id}")
        else:
            raise ValueError("서명자가 계약 당사자가 아닙니다")

        # 양측 서명 완료 시 ACTIVE
        if contract.provider_signature and contract.consumer_signature:
            contract.status = "ACTIVE"
            logger.info(f"🟢 계약 발효: {contract_id}")

        await db.flush()
        return self._serialize_contract(contract)

    async def verify_contract(
        self,
        db: AsyncSession,
        contract_id: str,
        requester_did: str,
    ) -> dict:
        """
        계약 유효성 검증
        데이터 접근 전 반드시 호출
        """
        result = await db.execute(
            select(DataContract).where(DataContract.contract_id == contract_id)
        )
        contract = result.scalar_one_or_none()

        if not contract:
            return {"valid": False, "reason": "계약을 찾을 수 없습니다"}

        if contract.status != "ACTIVE":
            return {"valid": False, "reason": f"계약이 활성 상태가 아닙니다: {contract.status}"}

        if datetime.utcnow() > contract.end_date:
            contract.status = "EXPIRED"
            await db.flush()
            return {"valid": False, "reason": "계약이 만료되었습니다"}

        if requester_did not in [contract.provider_did, contract.consumer_did]:
            return {"valid": False, "reason": "계약 당사자가 아닙니다"}

        return {
            "valid": True,
            "contract_id": contract_id,
            "provider": contract.provider_did,
            "consumer": contract.consumer_did,
            "dataset_id": contract.dataset_id,
            "policy_id": contract.policy_id,
            "status": contract.status,
            "valid_until": contract.end_date.isoformat(),
        }

    async def terminate_contract(self, db: AsyncSession, contract_id: str) -> bool:
        """계약 종료"""
        result = await db.execute(
            select(DataContract).where(DataContract.contract_id == contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            return False
        contract.status = "TERMINATED"
        await db.flush()
        logger.info(f"계약 종료: {contract_id}")
        return True

    async def list_contracts(
        self,
        db: AsyncSession,
        did: Optional[str] = None
    ) -> list:
        """계약 목록 조회"""
        query = select(DataContract)
        if did:
            from sqlalchemy import or_
            query = query.where(
                or_(DataContract.provider_did == did, DataContract.consumer_did == did)
            )
        result = await db.execute(query)
        contracts = result.scalars().all()
        return [self._serialize_contract(c) for c in contracts]

    def _serialize_contract(self, c: DataContract) -> dict:
        return {
            "contract_id": c.contract_id,
            "provider_did": c.provider_did,
            "consumer_did": c.consumer_did,
            "dataset_id": c.dataset_id,
            "policy_id": c.policy_id,
            "status": c.status,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "provider_signed": bool(c.provider_signature),
            "consumer_signed": bool(c.consumer_signature),
            "terms": c.terms,
        }


# 싱글톤
contract_manager = ContractManager()
