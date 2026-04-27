"""
Agentic AI 모듈
AI 에이전트가 자동으로 메타데이터 생성, 온톨로지 매핑, 카탈로그 등록 수행
"""

import uuid
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from identity.did import did_manager
from identity.vc import vc_manager
from metadata.extractor import metadata_extractor
from semantic.ontology_mapper import ontology_mapper
from connector.data_plane import data_plane
import logging

logger = logging.getLogger(__name__)


class KMXAgent:
    """
    KMX 자동화 에이전트

    에이전트 워크플로우:
    1. DID 보유 (Agentic Identity)
    2. 위임 VC 수신 (사용자 → 에이전트)
    3. 자율적 작업 수행:
       - 메타데이터 추출
       - 온톨로지 매핑
       - 카탈로그 등록
       - API 초안 생성
    """

    def __init__(self, agent_name: str = "KMX-AutoAgent-v1"):
        self.agent_name = agent_name
        self.agent_did = None
        self.delegation_vc = None
        self.task_log = []

    async def initialize(self, db: AsyncSession) -> dict:
        """에이전트 DID 생성 (Agentic Identity)"""
        did_info = await did_manager.create_did(
            db=db,
            controller=self.agent_name,
            entity_type="agent",
        )
        self.agent_did = did_info["did"]
        logger.info(f"✅ 에이전트 DID 생성: {self.agent_did}")
        return did_info

    async def receive_delegation(
        self,
        db: AsyncSession,
        human_did: str,
        permissions: list = None,
    ) -> dict:
        """사용자로부터 권한 위임 VC 수신"""
        if not self.agent_did:
            await self.initialize(db)

        permissions = permissions or [
            "metadata:create",
            "catalog:register",
            "ontology:map",
            "api:draft",
        ]

        delegation_vc = await vc_manager.issue_delegation_vc(
            db=db,
            human_did=human_did,
            agent_did=self.agent_did,
            permissions=permissions,
        )
        self.delegation_vc = delegation_vc
        logger.info(f"✅ 위임 VC 수신: {delegation_vc['id']}")
        return delegation_vc

    async def auto_catalog_dataset(
        self,
        db: AsyncSession,
        data: list,
        dataset_name: str,
        owner_did: str,
        policy_id: Optional[str] = None,
    ) -> dict:
        """
        자동 카탈로그 생성 워크플로우

        Step 1: 메타데이터 자동 추출
        Step 2: 온톨로지 매핑
        Step 3: 데이터 플레인 등록
        Step 4: 카탈로그 저장
        Step 5: API 초안 생성
        """
        task_id = f"task:{uuid.uuid4().hex[:12]}"
        steps = []
        start = datetime.utcnow()

        logger.info(f"🤖 에이전트 자동 카탈로그 시작: {dataset_name}")

        # Step 1: 메타데이터 추출
        steps.append({"step": 1, "name": "메타데이터 추출", "status": "running"})
        metadata = metadata_extractor.extract_from_json(data, f"{dataset_name}.json")
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {
            "columns": len(metadata.get("columns", [])),
            "rows": metadata.get("row_count", 0),
            "keywords": metadata.get("keywords", []),
        }

        # Step 2: 메타데이터 저장
        dataset_id = f"dataset:kmx:{uuid.uuid4().hex[:16]}"
        saved = await metadata_extractor.save_metadata(
            db=db,
            metadata=metadata,
            owner_did=owner_did,
            dataset_id=dataset_id,
            policy_id=policy_id,
        )

        # Step 3: 온톨로지 매핑
        steps.append({"step": 2, "name": "온톨로지 매핑", "status": "running"})
        columns = [col.get("name", "") if isinstance(col, dict) else col
                   for col in metadata.get("columns", [])]
        mapping_result = await ontology_mapper.map_and_save(db, dataset_id, columns)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {
            "mapped": mapping_result["mapped_count"],
            "total": mapping_result["total_columns"],
            "coverage": mapping_result["coverage"],
        }

        # Step 4: 데이터 플레인 등록
        steps.append({"step": 3, "name": "데이터 플레인 등록", "status": "running"})
        await data_plane.register_dataset(dataset_id, data, owner_did)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {"dataset_id": dataset_id}

        # Step 5: API 초안 생성
        steps.append({"step": 4, "name": "API 초안 생성", "status": "running"})
        api_draft = self._generate_api_draft(dataset_id, metadata)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {"endpoints": len(api_draft["endpoints"])}

        elapsed = (datetime.utcnow() - start).total_seconds()

        result = {
            "task_id": task_id,
            "agent_did": self.agent_did,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "status": "COMPLETED",
            "steps": steps,
            "elapsed_seconds": round(elapsed, 3),
            "metadata_summary": {
                "title": metadata.get("title"),
                "rows": metadata.get("row_count"),
                "columns": len(metadata.get("columns", [])),
                "keywords": metadata.get("keywords", []),
            },
            "ontology_coverage": mapping_result["coverage"],
            "api_draft": api_draft,
        }

        self.task_log.append({
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat(),
            "dataset_id": dataset_id,
        })

        logger.info(f"🤖 에이전트 작업 완료: {task_id} ({elapsed:.2f}s)")
        return result

    def _generate_api_draft(self, dataset_id: str, metadata: dict) -> dict:
        """데이터셋 API 초안 자동 생성"""
        columns = metadata.get("columns", [])
        col_names = [c.get("name", "") if isinstance(c, dict) else c for c in columns]

        return {
            "title": f"{metadata.get('title', 'Dataset')} API",
            "base_url": f"/api/v1/data/{dataset_id}",
            "version": "1.0.0",
            "endpoints": [
                {
                    "method": "GET",
                    "path": f"/api/v1/data/{dataset_id}",
                    "description": "데이터셋 전체 조회",
                    "parameters": [
                        {"name": "limit", "type": "integer", "default": 100},
                        {"name": "offset", "type": "integer", "default": 0},
                        {"name": "format", "type": "string", "default": "json"},
                    ],
                    "response": {"type": "array", "items": {col: "any" for col in col_names}},
                },
                {
                    "method": "GET",
                    "path": f"/api/v1/data/{dataset_id}/metadata",
                    "description": "데이터셋 메타데이터 조회",
                    "response": {"type": "object"},
                },
                {
                    "method": "POST",
                    "path": f"/api/v1/data/{dataset_id}/query",
                    "description": "데이터셋 조건부 쿼리",
                    "body": {
                        "filters": "object",
                        "columns": "array",
                        "limit": "integer",
                    },
                    "response": {"type": "array"},
                },
            ],
            "security": {
                "scheme": "DID-VC",
                "required": ["valid_contract", "odrl_permission"],
                "vc_types": ["MembershipVC", "DataAccessVC"],
            },
            "dcat_link": f"/api/v1/metadata/{dataset_id}",
        }

    async def run_health_check(self) -> dict:
        """에이전트 상태 확인"""
        return {
            "agent": self.agent_name,
            "agent_did": self.agent_did,
            "status": "ACTIVE" if self.agent_did else "UNINITIALIZED",
            "tasks_completed": len(self.task_log),
            "delegation_active": bool(self.delegation_vc),
            "capabilities": [
                "metadata_extraction",
                "ontology_mapping",
                "catalog_registration",
                "api_generation",
            ],
        }


# 기본 에이전트 인스턴스
default_agent = KMXAgent("KMX-AutoAgent-v1")
"""
Agentic AI 모듈
AI 에이전트가 자동으로 메타데이터 생성, 온톨로지 매핑, 카탈로그 등록 수행
"""

import uuid
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from identity.did import did_manager
from identity.vc import vc_manager
from metadata.extractor import metadata_extractor
from semantic.ontology_mapper import ontology_mapper
from connector.data_plane import data_plane
import logging

logger = logging.getLogger(__name__)


class KMXAgent:
    """
    KMX 자동화 에이전트
    
    에이전트 워크플로우:
    1. DID 보유 (Agentic Identity)
    2. 위임 VC 수신 (사용자 → 에이전트)
    3. 자율적 작업 수행:
       - 메타데이터 추출
       - 온톨로지 매핑
       - 카탈로그 등록
       - API 초안 생성
    """

    def __init__(self, agent_name: str = "KMX-AutoAgent-v1"):
        self.agent_name = agent_name
        self.agent_did = None
        self.delegation_vc = None
        self.task_log = []

    async def initialize(self, db: AsyncSession) -> dict:
        """에이전트 DID 생성 (Agentic Identity)"""
        did_info = await did_manager.create_did(
            db=db,
            controller=self.agent_name,
            entity_type="agent",
        )
        self.agent_did = did_info["did"]
        logger.info(f"✅ 에이전트 DID 생성: {self.agent_did}")
        return did_info

    async def receive_delegation(
        self,
        db: AsyncSession,
        human_did: str,
        permissions: list = None,
    ) -> dict:
        """사용자로부터 권한 위임 VC 수신"""
        if not self.agent_did:
            await self.initialize(db)

        permissions = permissions or [
            "metadata:create",
            "catalog:register",
            "ontology:map",
            "api:draft",
        ]

        delegation_vc = await vc_manager.issue_delegation_vc(
            db=db,
            human_did=human_did,
            agent_did=self.agent_did,
            permissions=permissions,
        )
        self.delegation_vc = delegation_vc
        logger.info(f"✅ 위임 VC 수신: {delegation_vc['id']}")
        return delegation_vc

    async def auto_catalog_dataset(
        self,
        db: AsyncSession,
        data: list,
        dataset_name: str,
        owner_did: str,
        policy_id: Optional[str] = None,
    ) -> dict:
        """
        자동 카탈로그 생성 워크플로우
        
        Step 1: 메타데이터 자동 추출
        Step 2: 온톨로지 매핑
        Step 3: 데이터 플레인 등록
        Step 4: 카탈로그 저장
        Step 5: API 초안 생성
        """
        task_id = f"task:{uuid.uuid4().hex[:12]}"
        steps = []
        start = datetime.utcnow()

        logger.info(f"🤖 에이전트 자동 카탈로그 시작: {dataset_name}")

        # Step 1: 메타데이터 추출
        steps.append({"step": 1, "name": "메타데이터 추출", "status": "running"})
        metadata = metadata_extractor.extract_from_json(data, f"{dataset_name}.json")
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {
            "columns": len(metadata.get("columns", [])),
            "rows": metadata.get("row_count", 0),
            "keywords": metadata.get("keywords", []),
        }

        # Step 2: 메타데이터 저장
        dataset_id = f"dataset:kmx:{uuid.uuid4().hex[:16]}"
        saved = await metadata_extractor.save_metadata(
            db=db,
            metadata=metadata,
            owner_did=owner_did,
            dataset_id=dataset_id,
            policy_id=policy_id,
        )

        # Step 3: 온톨로지 매핑
        steps.append({"step": 2, "name": "온톨로지 매핑", "status": "running"})
        columns = [col.get("name", "") if isinstance(col, dict) else col
                   for col in metadata.get("columns", [])]
        mapping_result = await ontology_mapper.map_and_save(db, dataset_id, columns)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {
            "mapped": mapping_result["mapped_count"],
            "total": mapping_result["total_columns"],
            "coverage": mapping_result["coverage"],
        }

        # Step 4: 데이터 플레인 등록
        steps.append({"step": 3, "name": "데이터 플레인 등록", "status": "running"})
        await data_plane.register_dataset(dataset_id, data, owner_did)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {"dataset_id": dataset_id}

        # Step 5: API 초안 생성
        steps.append({"step": 4, "name": "API 초안 생성", "status": "running"})
        api_draft = self._generate_api_draft(dataset_id, metadata)
        steps[-1]["status"] = "done"
        steps[-1]["result"] = {"endpoints": len(api_draft["endpoints"])}

        elapsed = (datetime.utcnow() - start).total_seconds()

        result = {
            "task_id": task_id,
            "agent_did": self.agent_did,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "status": "COMPLETED",
            "steps": steps,
            "elapsed_seconds": round(elapsed, 3),
            "metadata_summary": {
                "title": metadata.get("title"),
                "rows": metadata.get("row_count"),
                "columns": len(metadata.get("columns", [])),
                "keywords": metadata.get("keywords", []),
            },
            "ontology_coverage": mapping_result["coverage"],
            "api_draft": api_draft,
        }

        self.task_log.append({
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat(),
            "dataset_id": dataset_id,
        })

        logger.info(f"🤖 에이전트 작업 완료: {task_id} ({elapsed:.2f}s)")
        return result

    def _generate_api_draft(self, dataset_id: str, metadata: dict) -> dict:
        """데이터셋 API 초안 자동 생성"""
        columns = metadata.get("columns", [])
        col_names = [c.get("name", "") if isinstance(c, dict) else c for c in columns]

        return {
            "title": f"{metadata.get('title', 'Dataset')} API",
            "base_url": f"/api/v1/data/{dataset_id}",
            "version": "1.0.0",
            "endpoints": [
                {
                    "method": "GET",
                    "path": f"/api/v1/data/{dataset_id}",
                    "description": "데이터셋 전체 조회",
                    "parameters": [
                        {"name": "limit", "type": "integer", "default": 100},
                        {"name": "offset", "type": "integer", "default": 0},
                        {"name": "format", "type": "string", "default": "json"},
                    ],
                    "response": {"type": "array", "items": {col: "any" for col in col_names}},
                },
                {
                    "method": "GET",
                    "path": f"/api/v1/data/{dataset_id}/metadata",
                    "description": "데이터셋 메타데이터 조회",
                    "response": {"type": "object"},
                },
                {
                    "method": "POST",
                    "path": f"/api/v1/data/{dataset_id}/query",
                    "description": "데이터셋 조건부 쿼리",
                    "body": {
                        "filters": "object",
                        "columns": "array",
                        "limit": "integer",
                    },
                    "response": {"type": "array"},
                },
            ],
            "security": {
                "scheme": "DID-VC",
                "required": ["valid_contract", "odrl_permission"],
                "vc_types": ["MembershipVC", "DataAccessVC"],
            },
            "dcat_link": f"/api/v1/metadata/{dataset_id}",
        }

    async def run_health_check(self) -> dict:
        """에이전트 상태 확인"""
        return {
            "agent": self.agent_name,
            "agent_did": self.agent_did,
            "status": "ACTIVE" if self.agent_did else "UNINITIALIZED",
            "tasks_completed": len(self.task_log),
            "delegation_active": bool(self.delegation_vc),
            "capabilities": [
                "metadata_extraction",
                "ontology_mapping",
                "catalog_registration",
                "api_generation",
            ],
        }


# 기본 에이전트 인스턴스
default_agent = KMXAgent("KMX-AutoAgent-v1")
