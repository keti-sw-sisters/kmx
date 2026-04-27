"""
AI 모델 API 라우터
5대 제조 AI 모델 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from ai.model_api import ai_models

router = APIRouter()


class PredictRequest(BaseModel):
    model_type: str  # predictive_maintenance | quality_inspection | ...
    input_data: dict


@router.post("/predict", summary="AI 예측 실행")
async def predict(req: PredictRequest, db: AsyncSession = Depends(get_db)):
    """
    제조 AI 모델 예측 실행

    **model_type 옵션:**
    - `predictive_maintenance`: 설비 고장 예측
    - `quality_inspection`: 품질 불량 탐지
    - `process_optimization`: 공정 파라미터 최적화
    - `demand_forecasting`: 수요 예측
    - `energy_optimization`: 에너지 최적화

    **예시 입력 (predictive_maintenance):**
    ```json
    {
      "model_type": "predictive_maintenance",
      "input_data": {
        "temperature": 85.5,
        "vibration": 1.8,
        "pressure": 2.3,
        "runtime_hours": 3500
      }
    }
    ```
    """
    try:
        return await ai_models.predict(db, req.model_type, req.input_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models", summary="AI 모델 목록")
async def list_models(db: AsyncSession = Depends(get_db)):
    """사용 가능한 AI 모델 목록"""
    # 초기화 보장
    await ai_models.initialize_models(db)
    return await ai_models.list_models(db)


@router.get("/models/{model_type}/metadata", summary="모델 메타데이터")
async def get_model_metadata(model_type: str, db: AsyncSession = Depends(get_db)):
    """AI 모델 메타데이터 (입출력 스키마 등)"""
    await ai_models.initialize_models(db)
    result = await ai_models.get_model_info(db, model_type)
    if not result:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다")
    return result


@router.get("/models/{model_type}/health", summary="모델 상태 확인")
async def model_health(model_type: str, db: AsyncSession = Depends(get_db)):
    """AI 모델 상태 확인"""
    await ai_models.initialize_models(db)
    info = await ai_models.get_model_info(db, model_type)
    if not info:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다")
    return {"model_type": model_type, "status": info["status"], "version": info["version"]}
"""
AI 모델 API 라우터
5대 제조 AI 모델 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from ai.model_api import ai_models

router = APIRouter()


class PredictRequest(BaseModel):
    model_type: str  # predictive_maintenance | quality_inspection | ...
    input_data: dict


@router.post("/predict", summary="AI 예측 실행")
async def predict(req: PredictRequest, db: AsyncSession = Depends(get_db)):
    """
    제조 AI 모델 예측 실행
    
    **model_type 옵션:**
    - `predictive_maintenance`: 설비 고장 예측
    - `quality_inspection`: 품질 불량 탐지
    - `process_optimization`: 공정 파라미터 최적화
    - `demand_forecasting`: 수요 예측
    - `energy_optimization`: 에너지 최적화
    
    **예시 입력 (predictive_maintenance):**
    ```json
    {
      "model_type": "predictive_maintenance",
      "input_data": {
        "temperature": 85.5,
        "vibration": 1.8,
        "pressure": 2.3,
        "runtime_hours": 3500
      }
    }
    ```
    """
    try:
        return await ai_models.predict(db, req.model_type, req.input_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models", summary="AI 모델 목록")
async def list_models(db: AsyncSession = Depends(get_db)):
    """사용 가능한 AI 모델 목록"""
    # 초기화 보장
    await ai_models.initialize_models(db)
    return await ai_models.list_models(db)


@router.get("/models/{model_type}/metadata", summary="모델 메타데이터")
async def get_model_metadata(model_type: str, db: AsyncSession = Depends(get_db)):
    """AI 모델 메타데이터 (입출력 스키마 등)"""
    await ai_models.initialize_models(db)
    result = await ai_models.get_model_info(db, model_type)
    if not result:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다")
    return result


@router.get("/models/{model_type}/health", summary="모델 상태 확인")
async def model_health(model_type: str, db: AsyncSession = Depends(get_db)):
    """AI 모델 상태 확인"""
    await ai_models.initialize_models(db)
    info = await ai_models.get_model_info(db, model_type)
    if not info:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다")
    return {"model_type": model_type, "status": info["status"], "version": info["version"]}