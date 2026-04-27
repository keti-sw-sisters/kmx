"""
온톨로지 매퍼
컬럼명 → 표준 개념 매핑
Manufacturing 도메인 온톨로지 적용
"""

import json
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import DatasetMetadata
import logging

logger = logging.getLogger(__name__)


# 제조 도메인 온톨로지 정의
# 실제는 OWL/RDF 파일로 관리
MANUFACTURING_ONTOLOGY = {
    "concepts": {
        "MachineTemperature": {
            "uri": "mfg:MachineTemperature",
            "label": "기계 온도",
            "unit": "celsius",
            "range": [0, 500],
            "aliases": ["temperature", "temp", "온도", "기온", "체온"],
            "parent": "PhysicalMeasurement",
        },
        "VibrationLevel": {
            "uri": "mfg:VibrationLevel",
            "label": "진동 수준",
            "unit": "g",
            "range": [0, 10],
            "aliases": ["vibration", "vib", "진동"],
            "parent": "PhysicalMeasurement",
        },
        "PressureValue": {
            "uri": "mfg:PressureValue",
            "label": "압력값",
            "unit": "bar",
            "range": [0, 100],
            "aliases": ["pressure", "psi", "압력", "기압"],
            "parent": "PhysicalMeasurement",
        },
        "EnergyConsumption": {
            "uri": "mfg:EnergyConsumption",
            "label": "에너지 소비량",
            "unit": "kWh",
            "range": [0, 10000],
            "aliases": ["energy", "kwh", "power", "에너지", "전력량", "전력", "electricity"],
            "parent": "ResourceConsumption",
        },
        "QualityScore": {
            "uri": "mfg:QualityScore",
            "label": "품질 점수",
            "unit": "ratio",
            "range": [0, 1],
            "aliases": ["quality", "품질", "yield", "수율", "합격률", "output_quality"],
            "parent": "QualityMeasurement",
        },
        "ProductionOutput": {
            "uri": "mfg:ProductionOutput",
            "label": "생산 수량",
            "unit": "count",
            "range": [0, None],
            "aliases": ["output", "quantity", "count", "생산량", "수량", "production"],
            "parent": "ProductionMetric",
        },
        "MachineIdentifier": {
            "uri": "mfg:MachineIdentifier",
            "label": "기계 식별자",
            "unit": None,
            "range": None,
            "aliases": ["machine_id", "machine", "equipment", "device", "기계", "설비"],
            "parent": "AssetIdentifier",
        },
        "Timestamp": {
            "uri": "mfg:Timestamp",
            "label": "타임스탬프",
            "unit": "ISO8601",
            "range": None,
            "aliases": ["timestamp", "datetime", "date", "time", "시간", "날짜"],
            "parent": "TemporalAttribute",
        },
        "DefectRate": {
            "uri": "mfg:DefectRate",
            "label": "불량률",
            "unit": "ratio",
            "range": [0, 1],
            "aliases": ["defect", "defect_rate", "불량", "불량률", "error_rate"],
            "parent": "QualityMeasurement",
        },
        "OperationalStatus": {
            "uri": "mfg:OperationalStatus",
            "label": "운전 상태",
            "unit": None,
            "range": None,
            "aliases": ["status", "state", "상태", "운전", "가동"],
            "parent": "OperationalAttribute",
        },
    },
    "namespaces": {
        "mfg": "https://kmx.kr/ontology/manufacturing#",
        "iso": "https://www.iso.org/standard/",
        "iec": "https://www.iec.ch/",
    }
}


class OntologyMapper:
    """컬럼명 → 온톨로지 개념 매핑"""

    def __init__(self):
        self.ontology = MANUFACTURING_ONTOLOGY

    def map_column(self, column_name: str) -> Optional[dict]:
        """
        단일 컬럼명을 온톨로지 개념으로 매핑

        Returns:
            매핑된 개념 정보 또는 None
        """
        col_lower = column_name.lower().strip()

        for concept_name, concept in self.ontology["concepts"].items():
            aliases = [a.lower() for a in concept.get("aliases", [])]
            if col_lower in aliases or any(alias in col_lower for alias in aliases):
                return {
                    "column": column_name,
                    "concept": concept_name,
                    "uri": concept["uri"],
                    "label": concept["label"],
                    "unit": concept["unit"],
                    "range": concept["range"],
                    "parent_class": concept["parent"],
                    "confidence": 1.0 if col_lower in aliases else 0.8,
                }

        return {
            "column": column_name,
            "concept": None,
            "uri": None,
            "label": column_name,
            "unit": None,
            "range": None,
            "parent_class": "UnknownAttribute",
            "confidence": 0.0,
        }

    def map_dataset(self, columns: list) -> dict:
        """
        데이터셋 전체 컬럼 매핑

        Returns:
            {column_name: concept_mapping}
        """
        mappings = {}
        for col in columns:
            col_name = col if isinstance(col, str) else col.get("name", "")
            mappings[col_name] = self.map_column(col_name)

        mapped_count = sum(1 for m in mappings.values() if m.get("concept"))
        total = len(mappings)

        return {
            "mappings": mappings,
            "coverage": round(mapped_count / total, 3) if total > 0 else 0.0,
            "mapped_count": mapped_count,
            "total_columns": total,
            "ontology_version": "mfg-v1.0",
        }

    async def map_and_save(
        self,
        db: AsyncSession,
        dataset_id: str,
        columns: list,
    ) -> dict:
        """온톨로지 매핑 후 DB에 저장"""
        result = await db.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise ValueError(f"데이터셋을 찾을 수 없습니다: {dataset_id}")

        mapping_result = self.map_dataset(columns)
        dataset.ontology_mappings = mapping_result
        await db.flush()

        logger.info(
            f"✅ 온톨로지 매핑 완료: {dataset_id} "
            f"({mapping_result['mapped_count']}/{mapping_result['total_columns']})"
        )
        return mapping_result

    def get_concept_detail(self, concept_name: str) -> Optional[dict]:
        """온톨로지 개념 상세 정보"""
        return self.ontology["concepts"].get(concept_name)

    def list_concepts(self) -> list:
        """전체 온톨로지 개념 목록"""
        return [
            {
                "name": name,
                "uri": c["uri"],
                "label": c["label"],
                "unit": c["unit"],
                "parent": c["parent"],
            }
            for name, c in self.ontology["concepts"].items()
        ]


# 싱글톤
ontology_mapper = OntologyMapper()
"""
온톨로지 매퍼
컬럼명 → 표준 개념 매핑
Manufacturing 도메인 온톨로지 적용
"""

import json
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import DatasetMetadata
import logging

logger = logging.getLogger(__name__)


# 제조 도메인 온톨로지 정의
# 실제는 OWL/RDF 파일로 관리
MANUFACTURING_ONTOLOGY = {
    "concepts": {
        "MachineTemperature": {
            "uri": "mfg:MachineTemperature",
            "label": "기계 온도",
            "unit": "celsius",
            "range": [0, 500],
            "aliases": ["temperature", "temp", "온도", "기온", "체온"],
            "parent": "PhysicalMeasurement",
        },
        "VibrationLevel": {
            "uri": "mfg:VibrationLevel",
            "label": "진동 수준",
            "unit": "g",
            "range": [0, 10],
            "aliases": ["vibration", "vib", "진동"],
            "parent": "PhysicalMeasurement",
        },
        "PressureValue": {
            "uri": "mfg:PressureValue",
            "label": "압력값",
            "unit": "bar",
            "range": [0, 100],
            "aliases": ["pressure", "psi", "압력", "기압"],
            "parent": "PhysicalMeasurement",
        },
        "EnergyConsumption": {
            "uri": "mfg:EnergyConsumption",
            "label": "에너지 소비량",
            "unit": "kWh",
            "range": [0, 10000],
            "aliases": ["energy", "kwh", "power", "에너지", "전력량", "전력", "electricity"],
            "parent": "ResourceConsumption",
        },
        "QualityScore": {
            "uri": "mfg:QualityScore",
            "label": "품질 점수",
            "unit": "ratio",
            "range": [0, 1],
            "aliases": ["quality", "품질", "yield", "수율", "합격률", "output_quality"],
            "parent": "QualityMeasurement",
        },
        "ProductionOutput": {
            "uri": "mfg:ProductionOutput",
            "label": "생산 수량",
            "unit": "count",
            "range": [0, None],
            "aliases": ["output", "quantity", "count", "생산량", "수량", "production"],
            "parent": "ProductionMetric",
        },
        "MachineIdentifier": {
            "uri": "mfg:MachineIdentifier",
            "label": "기계 식별자",
            "unit": None,
            "range": None,
            "aliases": ["machine_id", "machine", "equipment", "device", "기계", "설비"],
            "parent": "AssetIdentifier",
        },
        "Timestamp": {
            "uri": "mfg:Timestamp",
            "label": "타임스탬프",
            "unit": "ISO8601",
            "range": None,
            "aliases": ["timestamp", "datetime", "date", "time", "시간", "날짜"],
            "parent": "TemporalAttribute",
        },
        "DefectRate": {
            "uri": "mfg:DefectRate",
            "label": "불량률",
            "unit": "ratio",
            "range": [0, 1],
            "aliases": ["defect", "defect_rate", "불량", "불량률", "error_rate"],
            "parent": "QualityMeasurement",
        },
        "OperationalStatus": {
            "uri": "mfg:OperationalStatus",
            "label": "운전 상태",
            "unit": None,
            "range": None,
            "aliases": ["status", "state", "상태", "운전", "가동"],
            "parent": "OperationalAttribute",
        },
    },
    "namespaces": {
        "mfg": "https://kmx.kr/ontology/manufacturing#",
        "iso": "https://www.iso.org/standard/",
        "iec": "https://www.iec.ch/",
    }
}


class OntologyMapper:
    """컬럼명 → 온톨로지 개념 매핑"""

    def __init__(self):
        self.ontology = MANUFACTURING_ONTOLOGY

    def map_column(self, column_name: str) -> Optional[dict]:
        """
        단일 컬럼명을 온톨로지 개념으로 매핑
        
        Returns:
            매핑된 개념 정보 또는 None
        """
        col_lower = column_name.lower().strip()

        for concept_name, concept in self.ontology["concepts"].items():
            aliases = [a.lower() for a in concept.get("aliases", [])]
            if col_lower in aliases or any(alias in col_lower for alias in aliases):
                return {
                    "column": column_name,
                    "concept": concept_name,
                    "uri": concept["uri"],
                    "label": concept["label"],
                    "unit": concept["unit"],
                    "range": concept["range"],
                    "parent_class": concept["parent"],
                    "confidence": 1.0 if col_lower in aliases else 0.8,
                }

        return {
            "column": column_name,
            "concept": None,
            "uri": None,
            "label": column_name,
            "unit": None,
            "range": None,
            "parent_class": "UnknownAttribute",
            "confidence": 0.0,
        }

    def map_dataset(self, columns: list) -> dict:
        """
        데이터셋 전체 컬럼 매핑
        
        Returns:
            {column_name: concept_mapping}
        """
        mappings = {}
        for col in columns:
            col_name = col if isinstance(col, str) else col.get("name", "")
            mappings[col_name] = self.map_column(col_name)

        mapped_count = sum(1 for m in mappings.values() if m.get("concept"))
        total = len(mappings)

        return {
            "mappings": mappings,
            "coverage": round(mapped_count / total, 3) if total > 0 else 0.0,
            "mapped_count": mapped_count,
            "total_columns": total,
            "ontology_version": "mfg-v1.0",
        }

    async def map_and_save(
        self,
        db: AsyncSession,
        dataset_id: str,
        columns: list,
    ) -> dict:
        """온톨로지 매핑 후 DB에 저장"""
        result = await db.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise ValueError(f"데이터셋을 찾을 수 없습니다: {dataset_id}")

        mapping_result = self.map_dataset(columns)
        dataset.ontology_mappings = mapping_result
        await db.flush()

        logger.info(
            f"✅ 온톨로지 매핑 완료: {dataset_id} "
            f"({mapping_result['mapped_count']}/{mapping_result['total_columns']})"
        )
        return mapping_result

    def get_concept_detail(self, concept_name: str) -> Optional[dict]:
        """온톨로지 개념 상세 정보"""
        return self.ontology["concepts"].get(concept_name)

    def list_concepts(self) -> list:
        """전체 온톨로지 개념 목록"""
        return [
            {
                "name": name,
                "uri": c["uri"],
                "label": c["label"],
                "unit": c["unit"],
                "parent": c["parent"],
            }
            for name, c in self.ontology["concepts"].items()
        ]


# 싱글톤
ontology_mapper = OntologyMapper()
