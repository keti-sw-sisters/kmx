"""
데이터베이스 연결 및 초기화
SQLite (개발) / PostgreSQL (운영)
"""

import logging
import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base

logger = logging.getLogger(__name__)

# 환경변수에서 DB URL 읽기 (기본값: SQLite)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./kmx_platform.db"
)

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )
except ModuleNotFoundError as exc:
    if DATABASE_URL.startswith("sqlite+") and "_sqlite3" in str(exc):
        logger.warning(
            "SQLite 드라이버를 사용할 수 없습니다. "
            "Python sqlite3 모듈 포함 버전을 사용하거나 DATABASE_URL에 PostgreSQL URL을 설정하세요."
        )
        engine = None
    else:
        raise

AsyncSessionLocal = (
    sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    if engine is not None
    else None
)


async def init_db():
    """테이블 자동 생성"""
    if engine is None:
        logger.warning("DB 엔진이 없어 init_db를 건너뜁니다.")
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ 데이터베이스 테이블 초기화 완료")


async def get_db():
    """DB 세션 의존성 주입"""
    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "DB 엔진이 초기화되지 않았습니다. "
                "DATABASE_URL을 PostgreSQL URL로 지정하거나 sqlite3 포함 Python을 사용하세요."
            ),
        )
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()