"""
제조 AI 모델 API
5대 제조 AI 모델 구현
- Predictive Maintenance (예지보전)
- Quality Inspection (품질 검사)
- Process Optimization (공정 최적화)
- Demand Forecasting (수요 예측)
- Energy Optimization (에너지 최적화)
"""

import uuid
import random
import math
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import AIModel
import logging

logger = logging.getLogger(__name__)


class ManufacturingAIModels:
    """
    5대 제조 AI 모델
    실제 운영 시 ML 모델로 교체 가능한 인터페이스
    현재는 규칙 기반 + 통계 모델로 시뮬레이션
    """

    async def initialize_models(self, db: AsyncSession):
        """AI 모델 메타데이터 초기화"""
        models = [
            {
                "model_id": "model:predictive-maintenance:v1",
                "name": "예지보전 모델",
                "model_type": "predictive_maintenance",
                "description": "설비 센서 데이터로 고장 예측",
                "input_schema": {
                    "temperature": "float",
                    "vibration": "float",
                    "pressure": "float",
                    "runtime_hours": "float"
                },
                "output_schema": {
                    "failure_probability": "float [0-1]",
                    "estimated_rul_hours": "int",
                    "risk_level": "string",
                    "recommended_action": "string"
                }
            },
            {
                "model_id": "model:quality-inspection:v1",
                "name": "품질 검사 모델",
                "model_type": "quality_inspection",
                "description": "생산 파라미터로 품질 불량 탐지",
                "input_schema": {
                    "temperature": "float",
                    "pressure": "float",
                    "speed": "float",
                    "material_grade": "string"
                },
                "output_schema": {
                    "defect_probability": "float [0-1]",
                    "quality_grade": "string",
                    "defect_type": "string",
                    "confidence": "float"
                }
            },
            {
                "model_id": "model:process-optimization:v1",
                "name": "공정 최적화 모델",
                "model_type": "process_optimization",
                "description": "생산 파라미터 최적화 추천",
                "input_schema": {
                    "current_parameters": "dict",
                    "target_output": "float",
                    "constraints": "dict"
                },
                "output_schema": {
                    "optimized_parameters": "dict",
                    "expected_improvement": "float",
                    "optimization_score": "float"
                }
            },
            {
                "model_id": "model:demand-forecasting:v1",
                "name": "수요 예측 모델",
                "model_type": "demand_forecasting",
                "description": "시계열 데이터 기반 수요 예측",
                "input_schema": {
                    "historical_demand": "list[float]",
                    "forecast_horizon": "int",
                    "seasonality": "string"
                },
                "output_schema": {
                    "forecast": "list[float]",
                    "confidence_interval": "dict",
                    "trend": "string"
                }
            },
            {
                "model_id": "model:energy-optimization:v1",
                "name": "에너지 최적화 모델",
                "model_type": "energy_optimization",
                "description": "에너지 소비 최적화 및 절감 방안",
                "input_schema": {
                    "energy_consumption": "list[float]",
                    "production_schedule": "dict",
                    "peak_hours": "list[int]"
                },
                "output_schema": {
                    "optimized_schedule": "dict",
                    "estimated_savings_kwh": "float",
                    "estimated_savings_krw": "float",
                    "recommendations": "list[string]"
                }
            }
        ]

        for m in models:
            existing = await db.execute(
                select(AIModel).where(AIModel.model_id == m["model_id"])
            )
            if not existing.scalar_one_or_none():
                db.add(AIModel(**m))

        await db.flush()
        logger.info("✅ AI 모델 초기화 완료")

    async def predict(
        self,
        db: AsyncSession,
        model_type: str,
        input_data: dict,
    ) -> dict:
        """
        AI 예측 실행

        Args:
            model_type: predictive_maintenance | quality_inspection |
                       process_optimization | demand_forecasting | energy_optimization
            input_data: 모델별 입력 데이터
        """
        handlers = {
            "predictive_maintenance": self._predict_maintenance,
            "quality_inspection": self._predict_quality,
            "process_optimization": self._optimize_process,
            "demand_forecasting": self._forecast_demand,
            "energy_optimization": self._optimize_energy,
        }

        handler = handlers.get(model_type)
        if not handler:
            raise ValueError(f"알 수 없는 모델 타입: {model_type}")

        prediction_id = f"pred:{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        result = handler(input_data)

        elapsed_ms = (datetime.utcnow() - start_time).microseconds / 1000

        logger.info(f"✅ AI 예측 완료: {model_type} ({elapsed_ms:.1f}ms)")
        return {
            "prediction_id": prediction_id,
            "model_type": model_type,
            "model_id": f"model:{model_type}:v1",
            "input": input_data,
            "output": result,
            "inference_ms": elapsed_ms,
            "timestamp": start_time.isoformat(),
        }

    def _predict_maintenance(self, data: dict) -> dict:
        """예지보전 예측 (규칙 기반 시뮬레이션)"""
        temp = float(data.get("temperature", 70))
        vibration = float(data.get("vibration", 0.5))
        pressure = float(data.get("pressure", 2.0))
        runtime = float(data.get("runtime_hours", 1000))

        # 위험도 스코어 계산
        score = 0.0
        score += min((temp - 60) / 40, 1.0) * 0.3  # 온도 기여도
        score += min(vibration / 3.0, 1.0) * 0.3    # 진동 기여도
        score += min((pressure - 1.0) / 2.0, 1.0) * 0.2  # 압력 기여도
        score += min(runtime / 5000, 1.0) * 0.2     # 운전시간 기여도

        failure_prob = round(min(score + random.uniform(-0.05, 0.05), 1.0), 3)
        rul = max(int((1 - failure_prob) * 2000 - runtime * 0.1), 0)

        if failure_prob < 0.2:
            risk = "LOW"
            action = "정기 점검 일정 유지"
        elif failure_prob < 0.5:
            risk = "MEDIUM"
            action = "1주일 내 점검 권고"
        elif failure_prob < 0.75:
            risk = "HIGH"
            action = "48시간 내 긴급 점검 필요"
        else:
            risk = "CRITICAL"
            action = "즉시 가동 중단 및 정비 필요"

        return {
            "failure_probability": failure_prob,
            "estimated_rul_hours": rul,
            "risk_level": risk,
            "recommended_action": action,
            "contributing_factors": {
                "temperature": round(min((temp - 60) / 40, 1.0) * 0.3, 3),
                "vibration": round(min(vibration / 3.0, 1.0) * 0.3, 3),
                "pressure": round(min((pressure - 1.0) / 2.0, 1.0) * 0.2, 3),
                "runtime": round(min(runtime / 5000, 1.0) * 0.2, 3),
            }
        }

    def _predict_quality(self, data: dict) -> dict:
        """품질 검사 예측"""
        temp = float(data.get("temperature", 70))
        pressure = float(data.get("pressure", 2.0))
        speed = float(data.get("speed", 100))

        defect_prob = 0.0
        if temp > 85:
            defect_prob += 0.3
        if pressure > 2.5 or pressure < 1.5:
            defect_prob += 0.25
        if speed > 120:
            defect_prob += 0.2
        defect_prob += random.uniform(0, 0.1)
        defect_prob = round(min(defect_prob, 1.0), 3)

        if defect_prob < 0.1:
            grade = "A"
            defect_type = "None"
        elif defect_prob < 0.3:
            grade = "B"
            defect_type = "Minor Surface Defect"
        elif defect_prob < 0.6:
            grade = "C"
            defect_type = "Dimensional Deviation"
        else:
            grade = "F"
            defect_type = "Critical Structural Defect"

        return {
            "defect_probability": defect_prob,
            "quality_grade": grade,
            "defect_type": defect_type,
            "confidence": round(1.0 - random.uniform(0.05, 0.15), 3),
            "inspection_result": "PASS" if defect_prob < 0.3 else "FAIL",
        }

    def _optimize_process(self, data: dict) -> dict:
        """공정 최적화"""
        current = data.get("current_parameters", {})
        target = float(data.get("target_output", 100))

        optimized = {}
        for key, val in current.items():
            if isinstance(val, (int, float)):
                optimized[key] = round(val * random.uniform(0.95, 1.05), 2)
            else:
                optimized[key] = val

        improvement = round(random.uniform(0.03, 0.15), 3)

        return {
            "optimized_parameters": optimized,
            "expected_improvement": improvement,
            "expected_output": round(target * (1 + improvement), 2),
            "optimization_score": round(random.uniform(0.7, 0.95), 3),
            "iterations": random.randint(50, 200),
        }

    def _forecast_demand(self, data: dict) -> dict:
        """수요 예측 (이동평균 기반)"""
        history = data.get("historical_demand", [100, 110, 105, 115, 120])
        horizon = int(data.get("forecast_horizon", 7))

        if not history:
            history = [100]

        avg = sum(history[-7:]) / min(len(history), 7)
        trend = (history[-1] - history[0]) / max(len(history) - 1, 1) if len(history) > 1 else 0

        forecast = []
        for i in range(horizon):
            val = avg + trend * (i + 1) + random.uniform(-avg * 0.05, avg * 0.05)
            forecast.append(round(max(val, 0), 2))

        return {
            "forecast": forecast,
            "confidence_interval": {
                "lower": [round(v * 0.9, 2) for v in forecast],
                "upper": [round(v * 1.1, 2) for v in forecast],
            },
            "trend": "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
            "avg_baseline": round(avg, 2),
        }

    def _optimize_energy(self, data: dict) -> dict:
        """에너지 최적화"""
        consumption = data.get("energy_consumption", [300, 280, 320, 310, 295])
        avg_consumption = sum(consumption) / len(consumption) if consumption else 300

        savings_pct = random.uniform(0.08, 0.18)
        savings_kwh = round(avg_consumption * savings_pct, 2)
        savings_krw = round(savings_kwh * 120, 0)  # 120원/kWh 기준

        return {
            "optimized_schedule": {
                "peak_load_shift": "09:00-11:00 → 14:00-16:00",
                "standby_reduction": "야간 대기전력 30% 감소",
            },
            "estimated_savings_kwh": savings_kwh,
            "estimated_savings_krw": savings_krw,
            "savings_percentage": round(savings_pct * 100, 1),
            "recommendations": [
                f"피크 시간대 부하 분산으로 {round(savings_kwh * 0.4, 1)} kWh 절감 가능",
                f"대기 전력 최소화로 {round(savings_kwh * 0.3, 1)} kWh 절감 가능",
                f"인버터 설비 교체 시 추가 {round(savings_kwh * 0.3, 1)} kWh 절감 가능",
            ],
        }

    async def get_model_info(self, db: AsyncSession, model_type: str) -> Optional[dict]:
        """모델 메타데이터 조회"""
        result = await db.execute(
            select(AIModel).where(AIModel.model_type == model_type)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return {
            "model_id": model.model_id,
            "name": model.name,
            "model_type": model.model_type,
            "version": model.version,
            "description": model.description,
            "input_schema": model.input_schema,
            "output_schema": model.output_schema,
            "status": model.status,
        }

    async def list_models(self, db: AsyncSession) -> list:
        """전체 모델 목록"""
        result = await db.execute(select(AIModel))
        models = result.scalars().all()
        return [
            {
                "model_id": m.model_id,
                "name": m.name,
                "model_type": m.model_type,
                "version": m.version,
                "status": m.status,
            }
            for m in models
        ]


# 싱글톤
ai_models = ManufacturingAIModels()
"""
제조 AI 모델 API
5대 제조 AI 모델 구현
- Predictive Maintenance (예지보전)
- Quality Inspection (품질 검사)
- Process Optimization (공정 최적화)
- Demand Forecasting (수요 예측)
- Energy Optimization (에너지 최적화)
"""

import uuid
import random
import math
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import AIModel
import logging

logger = logging.getLogger(__name__)


class ManufacturingAIModels:
    """
    5대 제조 AI 모델
    실제 운영 시 ML 모델로 교체 가능한 인터페이스
    현재는 규칙 기반 + 통계 모델로 시뮬레이션
    """

    async def initialize_models(self, db: AsyncSession):
        """AI 모델 메타데이터 초기화"""
        models = [
            {
                "model_id": "model:predictive-maintenance:v1",
                "name": "예지보전 모델",
                "model_type": "predictive_maintenance",
                "description": "설비 센서 데이터로 고장 예측",
                "input_schema": {
                    "temperature": "float",
                    "vibration": "float",
                    "pressure": "float",
                    "runtime_hours": "float"
                },
                "output_schema": {
                    "failure_probability": "float [0-1]",
                    "estimated_rul_hours": "int",
                    "risk_level": "string",
                    "recommended_action": "string"
                }
            },
            {
                "model_id": "model:quality-inspection:v1",
                "name": "품질 검사 모델",
                "model_type": "quality_inspection",
                "description": "생산 파라미터로 품질 불량 탐지",
                "input_schema": {
                    "temperature": "float",
                    "pressure": "float",
                    "speed": "float",
                    "material_grade": "string"
                },
                "output_schema": {
                    "defect_probability": "float [0-1]",
                    "quality_grade": "string",
                    "defect_type": "string",
                    "confidence": "float"
                }
            },
            {
                "model_id": "model:process-optimization:v1",
                "name": "공정 최적화 모델",
                "model_type": "process_optimization",
                "description": "생산 파라미터 최적화 추천",
                "input_schema": {
                    "current_parameters": "dict",
                    "target_output": "float",
                    "constraints": "dict"
                },
                "output_schema": {
                    "optimized_parameters": "dict",
                    "expected_improvement": "float",
                    "optimization_score": "float"
                }
            },
            {
                "model_id": "model:demand-forecasting:v1",
                "name": "수요 예측 모델",
                "model_type": "demand_forecasting",
                "description": "시계열 데이터 기반 수요 예측",
                "input_schema": {
                    "historical_demand": "list[float]",
                    "forecast_horizon": "int",
                    "seasonality": "string"
                },
                "output_schema": {
                    "forecast": "list[float]",
                    "confidence_interval": "dict",
                    "trend": "string"
                }
            },
            {
                "model_id": "model:energy-optimization:v1",
                "name": "에너지 최적화 모델",
                "model_type": "energy_optimization",
                "description": "에너지 소비 최적화 및 절감 방안",
                "input_schema": {
                    "energy_consumption": "list[float]",
                    "production_schedule": "dict",
                    "peak_hours": "list[int]"
                },
                "output_schema": {
                    "optimized_schedule": "dict",
                    "estimated_savings_kwh": "float",
                    "estimated_savings_krw": "float",
                    "recommendations": "list[string]"
                }
            }
        ]

        for m in models:
            existing = await db.execute(
                select(AIModel).where(AIModel.model_id == m["model_id"])
            )
            if not existing.scalar_one_or_none():
                db.add(AIModel(**m))

        await db.flush()
        logger.info("✅ AI 모델 초기화 완료")

    async def predict(
        self,
        db: AsyncSession,
        model_type: str,
        input_data: dict,
    ) -> dict:
        """
        AI 예측 실행
        
        Args:
            model_type: predictive_maintenance | quality_inspection | 
                       process_optimization | demand_forecasting | energy_optimization
            input_data: 모델별 입력 데이터
        """
        handlers = {
            "predictive_maintenance": self._predict_maintenance,
            "quality_inspection": self._predict_quality,
            "process_optimization": self._optimize_process,
            "demand_forecasting": self._forecast_demand,
            "energy_optimization": self._optimize_energy,
        }

        handler = handlers.get(model_type)
        if not handler:
            raise ValueError(f"알 수 없는 모델 타입: {model_type}")

        prediction_id = f"pred:{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        result = handler(input_data)

        elapsed_ms = (datetime.utcnow() - start_time).microseconds / 1000

        logger.info(f"✅ AI 예측 완료: {model_type} ({elapsed_ms:.1f}ms)")
        return {
            "prediction_id": prediction_id,
            "model_type": model_type,
            "model_id": f"model:{model_type}:v1",
            "input": input_data,
            "output": result,
            "inference_ms": elapsed_ms,
            "timestamp": start_time.isoformat(),
        }

    def _predict_maintenance(self, data: dict) -> dict:
        """예지보전 예측 (규칙 기반 시뮬레이션)"""
        temp = float(data.get("temperature", 70))
        vibration = float(data.get("vibration", 0.5))
        pressure = float(data.get("pressure", 2.0))
        runtime = float(data.get("runtime_hours", 1000))

        # 위험도 스코어 계산
        score = 0.0
        score += min((temp - 60) / 40, 1.0) * 0.3  # 온도 기여도
        score += min(vibration / 3.0, 1.0) * 0.3    # 진동 기여도
        score += min((pressure - 1.0) / 2.0, 1.0) * 0.2  # 압력 기여도
        score += min(runtime / 5000, 1.0) * 0.2     # 운전시간 기여도

        failure_prob = round(min(score + random.uniform(-0.05, 0.05), 1.0), 3)
        rul = max(int((1 - failure_prob) * 2000 - runtime * 0.1), 0)

        if failure_prob < 0.2:
            risk = "LOW"
            action = "정기 점검 일정 유지"
        elif failure_prob < 0.5:
            risk = "MEDIUM"
            action = "1주일 내 점검 권고"
        elif failure_prob < 0.75:
            risk = "HIGH"
            action = "48시간 내 긴급 점검 필요"
        else:
            risk = "CRITICAL"
            action = "즉시 가동 중단 및 정비 필요"

        return {
            "failure_probability": failure_prob,
            "estimated_rul_hours": rul,
            "risk_level": risk,
            "recommended_action": action,
            "contributing_factors": {
                "temperature": round(min((temp - 60) / 40, 1.0) * 0.3, 3),
                "vibration": round(min(vibration / 3.0, 1.0) * 0.3, 3),
                "pressure": round(min((pressure - 1.0) / 2.0, 1.0) * 0.2, 3),
                "runtime": round(min(runtime / 5000, 1.0) * 0.2, 3),
            }
        }

    def _predict_quality(self, data: dict) -> dict:
        """품질 검사 예측"""
        temp = float(data.get("temperature", 70))
        pressure = float(data.get("pressure", 2.0))
        speed = float(data.get("speed", 100))

        defect_prob = 0.0
        if temp > 85:
            defect_prob += 0.3
        if pressure > 2.5 or pressure < 1.5:
            defect_prob += 0.25
        if speed > 120:
            defect_prob += 0.2
        defect_prob += random.uniform(0, 0.1)
        defect_prob = round(min(defect_prob, 1.0), 3)

        if defect_prob < 0.1:
            grade = "A"
            defect_type = "None"
        elif defect_prob < 0.3:
            grade = "B"
            defect_type = "Minor Surface Defect"
        elif defect_prob < 0.6:
            grade = "C"
            defect_type = "Dimensional Deviation"
        else:
            grade = "F"
            defect_type = "Critical Structural Defect"

        return {
            "defect_probability": defect_prob,
            "quality_grade": grade,
            "defect_type": defect_type,
            "confidence": round(1.0 - random.uniform(0.05, 0.15), 3),
            "inspection_result": "PASS" if defect_prob < 0.3 else "FAIL",
        }

    def _optimize_process(self, data: dict) -> dict:
        """공정 최적화"""
        current = data.get("current_parameters", {})
        target = float(data.get("target_output", 100))

        optimized = {}
        for key, val in current.items():
            if isinstance(val, (int, float)):
                optimized[key] = round(val * random.uniform(0.95, 1.05), 2)
            else:
                optimized[key] = val

        improvement = round(random.uniform(0.03, 0.15), 3)

        return {
            "optimized_parameters": optimized,
            "expected_improvement": improvement,
            "expected_output": round(target * (1 + improvement), 2),
            "optimization_score": round(random.uniform(0.7, 0.95), 3),
            "iterations": random.randint(50, 200),
        }

    def _forecast_demand(self, data: dict) -> dict:
        """수요 예측 (이동평균 기반)"""
        history = data.get("historical_demand", [100, 110, 105, 115, 120])
        horizon = int(data.get("forecast_horizon", 7))

        if not history:
            history = [100]

        avg = sum(history[-7:]) / min(len(history), 7)
        trend = (history[-1] - history[0]) / max(len(history) - 1, 1) if len(history) > 1 else 0

        forecast = []
        for i in range(horizon):
            val = avg + trend * (i + 1) + random.uniform(-avg * 0.05, avg * 0.05)
            forecast.append(round(max(val, 0), 2))

        return {
            "forecast": forecast,
            "confidence_interval": {
                "lower": [round(v * 0.9, 2) for v in forecast],
                "upper": [round(v * 1.1, 2) for v in forecast],
            },
            "trend": "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
            "avg_baseline": round(avg, 2),
        }

    def _optimize_energy(self, data: dict) -> dict:
        """에너지 최적화"""
        consumption = data.get("energy_consumption", [300, 280, 320, 310, 295])
        avg_consumption = sum(consumption) / len(consumption) if consumption else 300

        savings_pct = random.uniform(0.08, 0.18)
        savings_kwh = round(avg_consumption * savings_pct, 2)
        savings_krw = round(savings_kwh * 120, 0)  # 120원/kWh 기준

        return {
            "optimized_schedule": {
                "peak_load_shift": "09:00-11:00 → 14:00-16:00",
                "standby_reduction": "야간 대기전력 30% 감소",
            },
            "estimated_savings_kwh": savings_kwh,
            "estimated_savings_krw": savings_krw,
            "savings_percentage": round(savings_pct * 100, 1),
            "recommendations": [
                f"피크 시간대 부하 분산으로 {round(savings_kwh * 0.4, 1)} kWh 절감 가능",
                f"대기 전력 최소화로 {round(savings_kwh * 0.3, 1)} kWh 절감 가능",
                f"인버터 설비 교체 시 추가 {round(savings_kwh * 0.3, 1)} kWh 절감 가능",
            ],
        }

    async def get_model_info(self, db: AsyncSession, model_type: str) -> Optional[dict]:
        """모델 메타데이터 조회"""
        result = await db.execute(
            select(AIModel).where(AIModel.model_type == model_type)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return {
            "model_id": model.model_id,
            "name": model.name,
            "model_type": model.model_type,
            "version": model.version,
            "description": model.description,
            "input_schema": model.input_schema,
            "output_schema": model.output_schema,
            "status": model.status,
        }

    async def list_models(self, db: AsyncSession) -> list:
        """전체 모델 목록"""
        result = await db.execute(select(AIModel))
        models = result.scalars().all()
        return [
            {
                "model_id": m.model_id,
                "name": m.name,
                "model_type": m.model_type,
                "version": m.version,
                "status": m.status,
            }
            for m in models
        ]


# 싱글톤
ai_models = ManufacturingAIModels()
