"""
DID (Decentralized Identifier) 관리 모듈
W3C DID Core 1.0 스펙 기반 구현
did:kmx:{method-specific-id} 형식
"""

import uuid
import hashlib
import json
import base64
from datetime import datetime
from typing import Optional
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import DID as DIDModel
import logging

logger = logging.getLogger(__name__)


class DIDManager:
    """DID 생성, 조회, 검증 관리자"""

    @staticmethod
    def _generate_keypair():
        """Ed25519 키쌍 생성"""
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )

        return (
            base64.b64encode(pub_bytes).decode(),
            base64.b64encode(priv_bytes).decode(),
            private_key
        )

    @staticmethod
    def build_did_document(did: str, public_key_b64: str, controller: str) -> dict:
        """W3C DID Document 생성"""
        return {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1"
            ],
            "id": did,
            "controller": controller,
            "verificationMethod": [
                {
                    "id": f"{did}#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": did,
                    "publicKeyMultibase": f"z{public_key_b64}"
                }
            ],
            "authentication": [f"{did}#key-1"],
            "assertionMethod": [f"{did}#key-1"],
            "service": [
                {
                    "id": f"{did}#kmx-connector",
                    "type": "KMXDataSpaceConnector",
                    "serviceEndpoint": "https://kmx.platform/connector"
                }
            ],
            "created": datetime.utcnow().isoformat() + "Z"
        }

    async def create_did(
        self,
        db: AsyncSession,
        controller: str,
        entity_type: str = "human"
    ) -> dict:
        """
        새 DID 생성 및 DB 저장
        
        Args:
            controller: DID 소유자 이름/ID
            entity_type: human | agent | connector
        """
        pub_b64, priv_b64, _ = self._generate_keypair()

        # did:kmx:{uuid} 형식
        method_id = hashlib.sha256(pub_b64.encode()).hexdigest()[:32]
        did = f"did:kmx:{method_id}"

        did_record = DIDModel(
            did=did,
            controller=controller,
            public_key=pub_b64,
            private_key_enc=priv_b64,  # 실제 운영 시 암호화 필요
            entity_type=entity_type,
        )
        db.add(did_record)
        await db.flush()

        did_document = self.build_did_document(did, pub_b64, controller)

        logger.info(f"✅ DID 생성 완료: {did} (type={entity_type})")
        return {
            "did": did,
            "did_document": did_document,
            "entity_type": entity_type,
            "controller": controller,
            "created_at": did_record.created_at.isoformat(),
        }

    async def resolve_did(self, db: AsyncSession, did: str) -> Optional[dict]:
        """DID 조회 (DID Resolution)"""
        result = await db.execute(select(DIDModel).where(DIDModel.did == did))
        record = result.scalar_one_or_none()
        if not record:
            return None
        return {
            "did": record.did,
            "controller": record.controller,
            "public_key": record.public_key,
            "entity_type": record.entity_type,
            "active": record.active,
            "did_document": self.build_did_document(record.did, record.public_key, record.controller),
        }

    async def list_dids(self, db: AsyncSession) -> list:
        """전체 DID 목록 조회"""
        result = await db.execute(select(DIDModel).where(DIDModel.active == True))
        records = result.scalars().all()
        return [
            {
                "did": r.did,
                "controller": r.controller,
                "entity_type": r.entity_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]

    def sign_data(self, private_key_b64: str, data: dict) -> str:
        """데이터 서명"""
        priv_bytes = base64.b64decode(private_key_b64)
        private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        message = json.dumps(data, sort_keys=True).encode()
        signature = private_key.sign(message)
        return base64.b64encode(signature).decode()

    def verify_signature(self, public_key_b64: str, data: dict, signature_b64: str) -> bool:
        """서명 검증"""
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub_bytes = base64.b64decode(public_key_b64)
            public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
            message = json.dumps(data, sort_keys=True).encode()
            signature = base64.b64decode(signature_b64)
            public_key.verify(signature, message)
            return True
        except Exception:
            return False


# 싱글톤 인스턴스
did_manager = DIDManager()
