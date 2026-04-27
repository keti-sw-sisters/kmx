"""
EDC Connector - Control Plane
IDS-RAM 기반 데이터 교환 제어 플레인
- 협상 처리
- 정책 검사
- 계약 관리
- 커넥터 레지스트리
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import ConnectorRegistry, DataContract, ODRLPolicy
from identity.vc import vc_manager
from policy.odrl_engine import odrl_engine
from contract.contract_manager import contract_manager
import logging
import httpx

logger = logging.getLogger(__name__)


class ControlPlane:
    """
    EDC Control Plane

    IDS-RAM 메시지 타입:
    - ContractRequestMessage: 계약 요청
    - ContractAgreementMessage: 계약 동의
    - ContractRejectionMessage: 계약 거절
    - ArtifactRequestMessage: 데이터 요청
    """

    async def register_connector(
        self,
        db: AsyncSession,
        name: str,
        owner_did: str,
        endpoint_url: str,
        capabilities: list = None,
        trust_level: str = "STANDARD",
    ) -> dict:
        """커넥터 레지스트리에 등록"""
        connector_id = f"connector:kmx:{uuid.uuid4().hex[:12]}"

        connector = ConnectorRegistry(
            connector_id=connector_id,
            name=name,
            owner_did=owner_did,
            endpoint_url=endpoint_url,
            capabilities=capabilities or ["data-transfer", "contract-negotiation"],
            trust_level=trust_level,
        )
        db.add(connector)
        await db.flush()

        logger.info(f"✅ 커넥터 등록: {connector_id} ({name})")
        return {
            "connector_id": connector_id,
            "name": name,
            "owner_did": owner_did,
            "endpoint_url": endpoint_url,
            "capabilities": capabilities,
            "trust_level": trust_level,
            "registered_at": connector.registered_at.isoformat(),
        }

    async def initiate_contract_negotiation(
        self,
        db: AsyncSession,
        consumer_did: str,
        provider_connector_id: str,
        dataset_id: str,
        policy_id: str,
        consumer_vc_id: Optional[str] = None,
    ) -> dict:
        """
        계약 협상 시작 (소비자 → 제공자)

        1. 소비자 VC 검증
        2. 정책 평가
        3. 계약 생성
        4. 제공자에게 ContractRequestMessage 전송
        """
        logger.info(f"계약 협상 시작: {consumer_did} → {provider_connector_id}")

        # 1. 소비자 VC 검증 (있는 경우)
        if consumer_vc_id:
            vc_result = await vc_manager.verify_vc(db, consumer_vc_id)
            if not vc_result["valid"]:
                return {
                    "success": False,
                    "stage": "VC_VERIFICATION",
                    "reason": f"VC 검증 실패: {vc_result['reason']}"
                }

        # 2. 제공자 커넥터 조회
        conn_result = await db.execute(
            select(ConnectorRegistry).where(
                ConnectorRegistry.connector_id == provider_connector_id,
                ConnectorRegistry.active == True
            )
        )
        provider_connector = conn_result.scalar_one_or_none()
        if not provider_connector:
            return {
                "success": False,
                "stage": "CONNECTOR_LOOKUP",
                "reason": "제공자 커넥터를 찾을 수 없습니다"
            }

        # 3. 정책 조회
        pol_result = await db.execute(
            select(ODRLPolicy).where(ODRLPolicy.policy_id == policy_id)
        )
        policy = pol_result.scalar_one_or_none()
        if not policy:
            return {
                "success": False,
                "stage": "POLICY_LOOKUP",
                "reason": "정책을 찾을 수 없습니다"
            }

        # 4. 정책 평가
        eval_result = await odrl_engine.evaluate_policy(
            db, policy_id, consumer_did, "use", {}
        )
        if not eval_result.permitted:
            return {
                "success": False,
                "stage": "POLICY_EVALUATION",
                "reason": eval_result.reason
            }

        # 5. 계약 생성
        contract = await contract_manager.create_contract(
            db=db,
            provider_did=provider_connector.owner_did,
            consumer_did=consumer_did,
            dataset_id=dataset_id,
            policy_id=policy_id,
        )

        # 6. 제공자 서명 (자동 - 실제는 제공자 확인 필요)
        contract = await contract_manager.sign_contract(
            db, contract["contract_id"], provider_connector.owner_did
        )

        logger.info(f"계약 협상 완료: {contract['contract_id']}")
        return {
            "success": True,
            "stage": "NEGOTIATION_COMPLETE",
            "contract": contract,
            "provider_connector": provider_connector_id,
            "message": "계약 협상이 완료되었습니다. 소비자 서명 후 데이터 접근 가능합니다.",
        }

    async def validate_data_request(
        self,
        db: AsyncSession,
        contract_id: str,
        requester_did: str,
        action: str = "use",
    ) -> dict:
        """
        데이터 요청 검증 (Data Plane 접근 전 호출)

        체크 순서:
        1. 계약 유효성
        2. ODRL 정책 평가
        """
        # 1. 계약 검증
        contract_check = await contract_manager.verify_contract(db, contract_id, requester_did)
        if not contract_check["valid"]:
            return {
                "authorized": False,
                "stage": "CONTRACT_CHECK",
                "reason": contract_check["reason"]
            }

        # 2. 정책 평가
        policy_result = await odrl_engine.evaluate_policy(
            db,
            contract_check["policy_id"],
            requester_did,
            action,
        )
        if not policy_result.permitted:
            return {
                "authorized": False,
                "stage": "POLICY_CHECK",
                "reason": policy_result.reason
            }

        return {
            "authorized": True,
            "contract_id": contract_id,
            "dataset_id": contract_check["dataset_id"],
            "requester": requester_did,
            "action": action,
            "authorized_at": datetime.utcnow().isoformat(),
        }

    async def list_connectors(self, db: AsyncSession) -> list:
        """등록된 커넥터 목록"""
        result = await db.execute(
            select(ConnectorRegistry).where(ConnectorRegistry.active == True)
        )
        connectors = result.scalars().all()
        return [
            {
                "connector_id": c.connector_id,
                "name": c.name,
                "owner_did": c.owner_did,
                "endpoint_url": c.endpoint_url,
                "capabilities": c.capabilities,
                "trust_level": c.trust_level,
                "registered_at": c.registered_at.isoformat(),
            }
            for c in connectors
        ]

    async def route_request(
        self,
        db: AsyncSession,
        target_connector_id: str,
        payload: dict,
    ) -> dict:
        """
        연합 커넥터 라우팅
        요청을 대상 커넥터로 전달
        """
        conn_result = await db.execute(
            select(ConnectorRegistry).where(
                ConnectorRegistry.connector_id == target_connector_id
            )
        )
        connector = conn_result.scalar_one_or_none()
        if not connector:
            return {"success": False, "reason": "커넥터를 찾을 수 없습니다"}

        # Mock: 실제 HTTP 전송 (외부 커넥터가 없어 시뮬레이션)
        logger.info(f"라우팅: → {connector.endpoint_url}")
        return {
            "success": True,
            "routed_to": connector.endpoint_url,
            "connector_id": target_connector_id,
            "payload_size": len(str(payload)),
            "timestamp": datetime.utcnow().isoformat(),
        }


# 싱글톤
control_plane = ControlPlane()
"""
EDC Connector - Control Plane
IDS-RAM 기반 데이터 교환 제어 플레인
- 협상 처리
- 정책 검사
- 계약 관리
- 커넥터 레지스트리
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import ConnectorRegistry, DataContract, ODRLPolicy
from identity.vc import vc_manager
from policy.odrl_engine import odrl_engine
from contract.contract_manager import contract_manager
import logging
import httpx

logger = logging.getLogger(__name__)


class ControlPlane:
    """
    EDC Control Plane
    
    IDS-RAM 메시지 타입:
    - ContractRequestMessage: 계약 요청
    - ContractAgreementMessage: 계약 동의
    - ContractRejectionMessage: 계약 거절
    - ArtifactRequestMessage: 데이터 요청
    """

    async def register_connector(
        self,
        db: AsyncSession,
        name: str,
        owner_did: str,
        endpoint_url: str,
        capabilities: list = None,
        trust_level: str = "STANDARD",
    ) -> dict:
        """커넥터 레지스트리에 등록"""
        connector_id = f"connector:kmx:{uuid.uuid4().hex[:12]}"

        connector = ConnectorRegistry(
            connector_id=connector_id,
            name=name,
            owner_did=owner_did,
            endpoint_url=endpoint_url,
            capabilities=capabilities or ["data-transfer", "contract-negotiation"],
            trust_level=trust_level,
        )
        db.add(connector)
        await db.flush()

        logger.info(f"✅ 커넥터 등록: {connector_id} ({name})")
        return {
            "connector_id": connector_id,
            "name": name,
            "owner_did": owner_did,
            "endpoint_url": endpoint_url,
            "capabilities": capabilities,
            "trust_level": trust_level,
            "registered_at": connector.registered_at.isoformat(),
        }

    async def initiate_contract_negotiation(
        self,
        db: AsyncSession,
        consumer_did: str,
        provider_connector_id: str,
        dataset_id: str,
        policy_id: str,
        consumer_vc_id: Optional[str] = None,
    ) -> dict:
        """
        계약 협상 시작 (소비자 → 제공자)
        
        1. 소비자 VC 검증
        2. 정책 평가
        3. 계약 생성
        4. 제공자에게 ContractRequestMessage 전송
        """
        logger.info(f"계약 협상 시작: {consumer_did} → {provider_connector_id}")

        # 1. 소비자 VC 검증 (있는 경우)
        if consumer_vc_id:
            vc_result = await vc_manager.verify_vc(db, consumer_vc_id)
            if not vc_result["valid"]:
                return {
                    "success": False,
                    "stage": "VC_VERIFICATION",
                    "reason": f"VC 검증 실패: {vc_result['reason']}"
                }

        # 2. 제공자 커넥터 조회
        conn_result = await db.execute(
            select(ConnectorRegistry).where(
                ConnectorRegistry.connector_id == provider_connector_id,
                ConnectorRegistry.active == True
            )
        )
        provider_connector = conn_result.scalar_one_or_none()
        if not provider_connector:
            return {
                "success": False,
                "stage": "CONNECTOR_LOOKUP",
                "reason": "제공자 커넥터를 찾을 수 없습니다"
            }

        # 3. 정책 조회
        pol_result = await db.execute(
            select(ODRLPolicy).where(ODRLPolicy.policy_id == policy_id)
        )
        policy = pol_result.scalar_one_or_none()
        if not policy:
            return {
                "success": False,
                "stage": "POLICY_LOOKUP",
                "reason": "정책을 찾을 수 없습니다"
            }

        # 4. 정책 평가
        eval_result = await odrl_engine.evaluate_policy(
            db, policy_id, consumer_did, "use", {}
        )
        if not eval_result.permitted:
            return {
                "success": False,
                "stage": "POLICY_EVALUATION",
                "reason": eval_result.reason
            }

        # 5. 계약 생성
        contract = await contract_manager.create_contract(
            db=db,
            provider_did=provider_connector.owner_did,
            consumer_did=consumer_did,
            dataset_id=dataset_id,
            policy_id=policy_id,
        )

        # 6. 제공자 서명 (자동 - 실제는 제공자 확인 필요)
        contract = await contract_manager.sign_contract(
            db, contract["contract_id"], provider_connector.owner_did
        )

        logger.info(f"계약 협상 완료: {contract['contract_id']}")
        return {
            "success": True,
            "stage": "NEGOTIATION_COMPLETE",
            "contract": contract,
            "provider_connector": provider_connector_id,
            "message": "계약 협상이 완료되었습니다. 소비자 서명 후 데이터 접근 가능합니다.",
        }

    async def validate_data_request(
        self,
        db: AsyncSession,
        contract_id: str,
        requester_did: str,
        action: str = "use",
    ) -> dict:
        """
        데이터 요청 검증 (Data Plane 접근 전 호출)
        
        체크 순서:
        1. 계약 유효성
        2. ODRL 정책 평가
        """
        # 1. 계약 검증
        contract_check = await contract_manager.verify_contract(db, contract_id, requester_did)
        if not contract_check["valid"]:
            return {
                "authorized": False,
                "stage": "CONTRACT_CHECK",
                "reason": contract_check["reason"]
            }

        # 2. 정책 평가
        policy_result = await odrl_engine.evaluate_policy(
            db,
            contract_check["policy_id"],
            requester_did,
            action,
        )
        if not policy_result.permitted:
            return {
                "authorized": False,
                "stage": "POLICY_CHECK",
                "reason": policy_result.reason
            }

        return {
            "authorized": True,
            "contract_id": contract_id,
            "dataset_id": contract_check["dataset_id"],
            "requester": requester_did,
            "action": action,
            "authorized_at": datetime.utcnow().isoformat(),
        }

    async def list_connectors(self, db: AsyncSession) -> list:
        """등록된 커넥터 목록"""
        result = await db.execute(
            select(ConnectorRegistry).where(ConnectorRegistry.active == True)
        )
        connectors = result.scalars().all()
        return [
            {
                "connector_id": c.connector_id,
                "name": c.name,
                "owner_did": c.owner_did,
                "endpoint_url": c.endpoint_url,
                "capabilities": c.capabilities,
                "trust_level": c.trust_level,
                "registered_at": c.registered_at.isoformat(),
            }
            for c in connectors
        ]

    async def route_request(
        self,
        db: AsyncSession,
        target_connector_id: str,
        payload: dict,
    ) -> dict:
        """
        연합 커넥터 라우팅
        요청을 대상 커넥터로 전달
        """
        conn_result = await db.execute(
            select(ConnectorRegistry).where(
                ConnectorRegistry.connector_id == target_connector_id
            )
        )
        connector = conn_result.scalar_one_or_none()
        if not connector:
            return {"success": False, "reason": "커넥터를 찾을 수 없습니다"}

        # Mock: 실제 HTTP 전송 (외부 커넥터가 없어 시뮬레이션)
        logger.info(f"라우팅: → {connector.endpoint_url}")
        return {
            "success": True,
            "routed_to": connector.endpoint_url,
            "connector_id": target_connector_id,
            "payload_size": len(str(payload)),
            "timestamp": datetime.utcnow().isoformat(),
        }


# 싱글톤
control_plane = ControlPlane()
