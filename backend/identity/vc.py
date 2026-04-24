"""
Verifiable Credentials (VC) 모듈
W3C VC Data Model 1.1 기반 구현
"""

import uuid
import json
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional, dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import VerifiableCredential as VCModel, DID as DIDModel
from identity.did import did_manager
import logging

logger = logging.getLogger(__name__)


class VCManager:
    """Verifiable Credential 발급 및 검증"""

    VC_TYPES = {
        "MembershipVC": "KMX 플랫폼 멤버십 자격증명",
        "ManufacturerVC": "제조업체 인증 자격증명",
        "DelegationVC": "에이전트 권한 위임 자격증명",
        "DataAccessVC": "데이터 접근 권한 자격증명",
    }

    async def issue_vc(
        self,
        db: AsyncSession,
        issuer_did: str,
        subject_did: str,
        vc_type: str,
        claims: dict,
        valid_days: int = 365,
    ) -> dict:
        """
        VC 발급
        
        Args:
            issuer_did: 발급자 DID (신뢰기관)
            subject_did: 주체 DID (VC 소유자)
            vc_type: VC 유형
            claims: 자격증명 클레임 데이터
            valid_days: 유효 기간(일)
        """
        # 발급자 DID 조회
        result = await db.execute(select(DIDModel).where(DIDModel.did == issuer_did))
        issuer = result.scalar_one_or_none()
        if not issuer:
            raise ValueError(f"발급자 DID를 찾을 수 없습니다: {issuer_did}")

        vc_id = f"vc:kmx:{uuid.uuid4().hex[:16]}"
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(days=valid_days)

        # VC 페이로드 구성
        vc_payload = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://kmx.kr/credentials/v1"
            ],
            "id": vc_id,
            "type": ["VerifiableCredential", vc_type],
            "issuer": {
                "id": issuer_did,
                "name": issuer.controller
            },
            "issuanceDate": issued_at.isoformat() + "Z",
            "expirationDate": expires_at.isoformat() + "Z",
            "credentialSubject": {
                "id": subject_did,
                **claims
            }
        }

        # 서명 생성
        signature = did_manager.sign_data(issuer.private_key_enc, vc_payload)

        # VC 저장
        vc_record = VCModel(
            vc_id=vc_id,
            issuer_did=issuer_did,
            subject_did=subject_did,
            vc_type=vc_type,
            claims=claims,
            issued_at=issued_at,
            expires_at=expires_at,
            signature=signature,
        )
        db.add(vc_record)
        await db.flush()

        # W3C VC 포맷으로 반환
        vc_payload["proof"] = {
            "type": "Ed25519Signature2020",
            "created": issued_at.isoformat() + "Z",
            "verificationMethod": f"{issuer_did}#key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": signature
        }

        logger.info(f"✅ VC 발급 완료: {vc_id} (type={vc_type})")
        return vc_payload

    async def verify_vc(self, db: AsyncSession, vc_id: str) -> dict:
        """VC 유효성 검증"""
        result = await db.execute(select(VCModel).where(VCModel.vc_id == vc_id))
        vc = result.scalar_one_or_none()

        if not vc:
            return {"valid": False, "reason": "VC를 찾을 수 없습니다"}

        if vc.revoked:
            return {"valid": False, "reason": "VC가 폐지되었습니다"}

        if vc.expires_at and datetime.utcnow() > vc.expires_at:
            return {"valid": False, "reason": "VC가 만료되었습니다"}

        # 발급자 공개키로 서명 검증
        issuer_result = await db.execute(select(DIDModel).where(DIDModel.did == vc.issuer_did))
        issuer = issuer_result.scalar_one_or_none()
        if not issuer:
            return {"valid": False, "reason": "발급자 DID를 찾을 수 없습니다"}

        vc_payload = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "id": vc.vc_id,
            "type": ["VerifiableCredential", vc.vc_type],
            "issuer": {"id": vc.issuer_did},
            "issuanceDate": vc.issued_at.isoformat() + "Z",
            "credentialSubject": {"id": vc.subject_did, **vc.claims}
        }
        sig_valid = did_manager.verify_signature(issuer.public_key, vc_payload, vc.signature)

        return {
            "valid": sig_valid,
            "vc_id": vc_id,
            "vc_type": vc.vc_type,
            "issuer": vc.issuer_did,
            "subject": vc.subject_did,
            "issued_at": vc.issued_at.isoformat(),
            "expires_at": vc.expires_at.isoformat() if vc.expires_at else None,
            "claims": vc.claims,
            "reason": None if sig_valid else "서명 검증 실패"
        }

    async def issue_delegation_vc(
        self,
        db: AsyncSession,
        human_did: str,
        agent_did: str,
        permissions: list,
        valid_hours: int = 24,
    ) -> dict:
        """
        에이전트 권한 위임 VC 발급
        사용자 → AI 에이전트 권한 위임
        """
        claims = {
            "delegator": human_did,
            "delegate": agent_did,
            "permissions": permissions,
            "delegationType": "AgentDelegation",
            "constraints": {
                "validFor": f"{valid_hours}h",
                "scope": "data-space-operations"
            }
        }
        return await self.issue_vc(
            db=db,
            issuer_did=human_did,
            subject_did=agent_did,
            vc_type="DelegationVC",
            claims=claims,
            valid_days=valid_hours / 24,
        )

    async def list_vcs(self, db: AsyncSession, subject_did: Optional[str] = None) -> list:
        """VC 목록 조회"""
        query = select(VCModel)
        if subject_did:
            query = query.where(VCModel.subject_did == subject_did)
        result = await db.execute(query)
        vcs = result.scalars().all()
        return [
            {
                "vc_id": vc.vc_id,
                "vc_type": vc.vc_type,
                "issuer": vc.issuer_did,
                "subject": vc.subject_did,
                "issued_at": vc.issued_at.isoformat(),
                "expires_at": vc.expires_at.isoformat() if vc.expires_at else None,
                "revoked": vc.revoked,
            }
            for vc in vcs
        ]

    async def revoke_vc(self, db: AsyncSession, vc_id: str) -> bool:
        """VC 폐지"""
        result = await db.execute(select(VCModel).where(VCModel.vc_id == vc_id))
        vc = result.scalar_one_or_none()
        if not vc:
            return False
        vc.revoked = True
        await db.flush()
        logger.info(f"VC 폐지: {vc_id}")
        return True


# 싱글톤
vc_manager = VCManager()
