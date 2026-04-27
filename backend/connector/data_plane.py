"""
EDC Connector - Data Plane
실제 데이터 전송 처리
P2P 방식 - 중앙 저장 없이 직접 전송
"""

import uuid
import hashlib
import json
import io
import csv
from datetime import datetime
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from connector.control_plane import control_plane
from clearinghouse.logger import clearing_logger
import logging

logger = logging.getLogger(__name__)


class DataPlane:
    """
    EDC Data Plane

    데이터 전송 방식:
    - HTTP Push: 제공자 → 소비자 직접 전송
    - HTTP Pull: 소비자가 제공자에서 직접 Pull

    데이터는 절대 플랫폼 서버에 저장하지 않음 (Data Sovereignty)
    """

    # 메모리 내 임시 데이터 저장소 (실제는 각 기업 내부 시스템)
    _data_store: dict = {}

    async def register_dataset(
        self,
        dataset_id: str,
        data: list,
        owner_did: str,
    ) -> dict:
        """데이터셋 등록 (제공자 측 데이터 플레인에 저장)"""
        self._data_store[dataset_id] = {
            "data": data,
            "owner_did": owner_did,
            "registered_at": datetime.utcnow().isoformat(),
            "access_count": 0,
        }
        logger.info(f"✅ 데이터셋 등록: {dataset_id} ({len(data)} rows)")
        return {"dataset_id": dataset_id, "rows": len(data)}

    async def transfer_data(
        self,
        db: AsyncSession,
        contract_id: str,
        dataset_id: str,
        requester_did: str,
        format: str = "json",
    ) -> dict:
        """
        데이터 전송 처리

        흐름:
        1. Control Plane에서 권한 검증
        2. 데이터 로드
        3. 전송 (P2P 방식)
        4. Clearing House에 로그 기록
        """
        # 1. Control Plane 권한 검증
        auth_result = await control_plane.validate_data_request(
            db, contract_id, requester_did, "use"
        )
        if not auth_result["authorized"]:
            return {
                "success": False,
                "reason": auth_result["reason"],
                "stage": auth_result.get("stage"),
            }

        # 2. 데이터 로드
        dataset = self._data_store.get(dataset_id)
        if not dataset:
            # 샘플 데이터 반환 (실제 연동 시 내부 DB/파일 시스템에서 로드)
            dataset = {
                "data": self._generate_sample_data(dataset_id),
                "owner_did": "did:kmx:provider",
            }

        data = dataset["data"]

        # 3. 포맷 변환
        if format == "csv":
            content = self._to_csv(data)
            content_type = "text/csv"
        else:
            content = data
            content_type = "application/json"

        # 4. 전송 메타데이터
        transfer_id = f"transfer:{uuid.uuid4().hex[:12]}"
        payload_hash = hashlib.sha256(
            json.dumps(data, ensure_ascii=False).encode()
        ).hexdigest()

        # 5. Clearing House 로그
        await clearing_logger.log_transfer(
            db=db,
            transfer_id=transfer_id,
            contract_id=contract_id,
            provider_did=dataset.get("owner_did", "unknown"),
            consumer_did=requester_did,
            dataset_id=dataset_id,
            bytes_transferred=len(json.dumps(data).encode()),
            status="SUCCESS",
            metadata={
                "format": format,
                "row_count": len(data) if isinstance(data, list) else 1,
                "payload_hash": payload_hash,
            }
        )

        # 접근 카운트 증가
        if dataset_id in self._data_store:
            self._data_store[dataset_id]["access_count"] += 1

        logger.info(f"✅ 데이터 전송 완료: {transfer_id}")
        return {
            "success": True,
            "transfer_id": transfer_id,
            "dataset_id": dataset_id,
            "contract_id": contract_id,
            "data": content,
            "content_type": content_type,
            "row_count": len(data) if isinstance(data, list) else 1,
            "payload_hash": payload_hash,
            "transferred_at": datetime.utcnow().isoformat(),
        }

    def _to_csv(self, data: list) -> str:
        """JSON → CSV 변환"""
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def _generate_sample_data(self, dataset_id: str) -> list:
        """샘플 제조 데이터 생성 (데모용)"""
        import random
        rows = []
        for i in range(10):
            rows.append({
                "timestamp": f"2024-{i+1:02d}-01T00:00:00Z",
                "machine_id": f"M-{random.randint(100, 999)}",
                "temperature": round(random.uniform(60, 95), 2),
                "vibration": round(random.uniform(0.1, 2.5), 3),
                "pressure": round(random.uniform(1.0, 3.0), 2),
                "output_quality": round(random.uniform(0.85, 0.99), 3),
                "energy_kwh": round(random.uniform(100, 500), 1),
            })
        return rows

    async def get_dataset_info(self, dataset_id: str) -> Optional[dict]:
        """데이터셋 정보 조회"""
        ds = self._data_store.get(dataset_id)
        if not ds:
            return None
        return {
            "dataset_id": dataset_id,
            "owner_did": ds["owner_did"],
            "registered_at": ds["registered_at"],
            "row_count": len(ds["data"]),
            "access_count": ds["access_count"],
        }


# 싱글톤
data_plane = DataPlane()
"""
EDC Connector - Data Plane
실제 데이터 전송 처리
P2P 방식 - 중앙 저장 없이 직접 전송
"""

import uuid
import hashlib
import json
import io
import csv
from datetime import datetime
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from connector.control_plane import control_plane
from clearinghouse.logger import clearing_logger
import logging

logger = logging.getLogger(__name__)


class DataPlane:
    """
    EDC Data Plane
    
    데이터 전송 방식:
    - HTTP Push: 제공자 → 소비자 직접 전송
    - HTTP Pull: 소비자가 제공자에서 직접 Pull
    
    데이터는 절대 플랫폼 서버에 저장하지 않음 (Data Sovereignty)
    """

    # 메모리 내 임시 데이터 저장소 (실제는 각 기업 내부 시스템)
    _data_store: dict = {}

    async def register_dataset(
        self,
        dataset_id: str,
        data: list,
        owner_did: str,
    ) -> dict:
        """데이터셋 등록 (제공자 측 데이터 플레인에 저장)"""
        self._data_store[dataset_id] = {
            "data": data,
            "owner_did": owner_did,
            "registered_at": datetime.utcnow().isoformat(),
            "access_count": 0,
        }
        logger.info(f"✅ 데이터셋 등록: {dataset_id} ({len(data)} rows)")
        return {"dataset_id": dataset_id, "rows": len(data)}

    async def transfer_data(
        self,
        db: AsyncSession,
        contract_id: str,
        dataset_id: str,
        requester_did: str,
        format: str = "json",
    ) -> dict:
        """
        데이터 전송 처리
        
        흐름:
        1. Control Plane에서 권한 검증
        2. 데이터 로드
        3. 전송 (P2P 방식)
        4. Clearing House에 로그 기록
        """
        # 1. Control Plane 권한 검증
        auth_result = await control_plane.validate_data_request(
            db, contract_id, requester_did, "use"
        )
        if not auth_result["authorized"]:
            return {
                "success": False,
                "reason": auth_result["reason"],
                "stage": auth_result.get("stage"),
            }

        # 2. 데이터 로드
        dataset = self._data_store.get(dataset_id)
        if not dataset:
            # 샘플 데이터 반환 (실제 연동 시 내부 DB/파일 시스템에서 로드)
            dataset = {
                "data": self._generate_sample_data(dataset_id),
                "owner_did": "did:kmx:provider",
            }

        data = dataset["data"]

        # 3. 포맷 변환
        if format == "csv":
            content = self._to_csv(data)
            content_type = "text/csv"
        else:
            content = data
            content_type = "application/json"

        # 4. 전송 메타데이터
        transfer_id = f"transfer:{uuid.uuid4().hex[:12]}"
        payload_hash = hashlib.sha256(
            json.dumps(data, ensure_ascii=False).encode()
        ).hexdigest()

        # 5. Clearing House 로그
        await clearing_logger.log_transfer(
            db=db,
            transfer_id=transfer_id,
            contract_id=contract_id,
            provider_did=dataset.get("owner_did", "unknown"),
            consumer_did=requester_did,
            dataset_id=dataset_id,
            bytes_transferred=len(json.dumps(data).encode()),
            status="SUCCESS",
            metadata={
                "format": format,
                "row_count": len(data) if isinstance(data, list) else 1,
                "payload_hash": payload_hash,
            }
        )

        # 접근 카운트 증가
        if dataset_id in self._data_store:
            self._data_store[dataset_id]["access_count"] += 1

        logger.info(f"✅ 데이터 전송 완료: {transfer_id}")
        return {
            "success": True,
            "transfer_id": transfer_id,
            "dataset_id": dataset_id,
            "contract_id": contract_id,
            "data": content,
            "content_type": content_type,
            "row_count": len(data) if isinstance(data, list) else 1,
            "payload_hash": payload_hash,
            "transferred_at": datetime.utcnow().isoformat(),
        }

    def _to_csv(self, data: list) -> str:
        """JSON → CSV 변환"""
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def _generate_sample_data(self, dataset_id: str) -> list:
        """샘플 제조 데이터 생성 (데모용)"""
        import random
        rows = []
        for i in range(10):
            rows.append({
                "timestamp": f"2024-{i+1:02d}-01T00:00:00Z",
                "machine_id": f"M-{random.randint(100, 999)}",
                "temperature": round(random.uniform(60, 95), 2),
                "vibration": round(random.uniform(0.1, 2.5), 3),
                "pressure": round(random.uniform(1.0, 3.0), 2),
                "output_quality": round(random.uniform(0.85, 0.99), 3),
                "energy_kwh": round(random.uniform(100, 500), 1),
            })
        return rows

    async def get_dataset_info(self, dataset_id: str) -> Optional[dict]:
        """데이터셋 정보 조회"""
        ds = self._data_store.get(dataset_id)
        if not ds:
            return None
        return {
            "dataset_id": dataset_id,
            "owner_did": ds["owner_did"],
            "registered_at": ds["registered_at"],
            "row_count": len(ds["data"]),
            "access_count": ds["access_count"],
        }


# 싱글톤
data_plane = DataPlane()
