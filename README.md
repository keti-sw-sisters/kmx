# KMX Platform — 한국형 Manufacturing-X 데이터 스페이스 플랫폼

> **데이터 스페이스 + AI + 거버넌스 통합 플랫폼 레퍼런스 구현23**  
> Korean Manufacturing-X (KMX) Data Space Platform

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                    KMX Platform Architecture                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   사용자/기업  │  │  AI 에이전트  │  │  외부 커넥터 (연합)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                       │              │
│  ╔══════╧═════════════════╧═══════════════════════╧══════╗      │
│  ║              Identity & Governance Layer               ║      │
│  ║  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   ║      │
│  ║  │  DID/VC  │  │  ODRL    │  │  Contract Manager │   ║      │
│  ║  │  관리     │  │  정책엔진 │  │  계약 관리        │   ║      │
│  ║  └──────────┘  └──────────┘  └───────────────────┘   ║      │
│  ╚═══════════════════════════════════════════════════════╝      │
│                                                                  │
│  ╔═════════════════════════════════════════════════════════╗     │
│  ║                 Data Space Layer                         ║     │
│  ║  ┌──────────────────┐    ┌─────────────────────────┐   ║     │
│  ║  │   Control Plane   │    │      Data Plane          │   ║     │
│  ║  │  - 계약 협상      │◄──►│  - P2P 데이터 전송      │   ║     │
│  ║  │  - 정책 검사      │    │  - 포맷 변환             │   ║     │
│  ║  │  - 커넥터 라우팅  │    │  - 데이터 주권 보장      │   ║     │
│  ║  └──────────────────┘    └─────────────────────────┘   ║     │
│  ╚═════════════════════════════════════════════════════════╝     │
│                                                                  │
│  ╔══════════════╗   ╔═══════════════════════════════════════╗    │
│  ║   AI Layer   ║   ║         Data Intelligence Layer       ║    │
│  ║  ┌─────────┐ ║   ║  ┌──────────┐  ┌──────────────────┐  ║    │
│  ║  │예지보전  │ ║   ║  │메타데이터 │  │  벡터 검색 엔진  │  ║    │
│  ║  │품질검사  │ ║   ║  │자동 추출  │  │  자연어 검색     │  ║    │
│  ║  │공정최적화│ ║   ║  └──────────┘  └──────────────────┘  ║    │
│  ║  │수요예측  │ ║   ║  ┌──────────┐  ┌──────────────────┐  ║    │
│  ║  │에너지최적│ ║   ║  │온톨로지  │  │  DCAT 카탈로그   │  ║    │
│  ║  └─────────┘ ║   ║  │매핑       │  │  데이터셋 등록   │  ║    │
│  ╚══════════════╝   ║  └──────────┘  └──────────────────┘  ║    │
│                     ╚═══════════════════════════════════════╝    │
│                                                                  │
│  ╔═════════════════════════════════════════════════════════╗     │
│  ║              Clearing House (공증/정산)                  ║     │
│  ║  해시체인 기반 불변 감사로그 · 사용량 기반 자동 정산     ║     │
│  ╚═════════════════════════════════════════════════════════╝     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 데이터 흐름 다이어그램

```
사용자 요청
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Agent 실행 (선택사항)                                     │
│   사용자 → 에이전트 권한 위임 (Delegation VC 발급)               │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: DID/VC 인증                                               │
│   - 요청자 DID 확인 (did:kmx:xxxx)                               │
│   - Verifiable Credential 유효성 검증                             │
│   - 서명 검증 (Ed25519)                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ ✅ 인증 통과
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Contract 확인 (Control Plane)                             │
│   - 데이터 사용 계약 존재 여부 확인                               │
│   - 계약 상태 확인 (ACTIVE)                                       │
│   - 계약 만료 여부 확인                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ ✅ 계약 유효
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: ODRL 정책 검사                                            │
│   - 요청 행위 (use/read/distribute) 허용 여부                     │
│   - 제약 조건 평가 (시간, 목적, 횟수)                             │
│   - Prohibition 우선 검사                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ ✅ 정책 허용
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Data Plane 데이터 전송                                    │
│   - P2P 직접 전송 (중앙 저장 없음)                                │
│   - 포맷 변환 (JSON/CSV)                                          │
│   - 페이로드 해시 생성                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Clearing House 로그 기록                                  │
│   - 해시체인 로그 생성                                             │
│   - 이전 로그와 연결 (위변조 방지)                                 │
│   - 사용량 정산 데이터 누적                                        │
└─────────────────────────────────────────────────────────────────┘
                         │
    ▼
          응답 반환 (데이터 + 전송 ID + 해시)
```

---

## 프로젝트 구조

```
kmx-platform/
├── backend/
│   ├── main.py                    # FastAPI 메인 앱
│   ├── requirements.txt
│   ├── test_core.py               # 핵심 로직 단위 테스트 (52개)
│   │
│   ├── api/                       # API 라우터
│   │   ├── connector_routes.py    # EDC 커넥터 API
│   │   ├── identity_routes.py     # DID/VC API
│   │   ├── policy_routes.py       # ODRL 정책 API
│   │   ├── contract_routes.py     # 계약 API
│   │   ├── metadata_routes.py     # 메타데이터/온톨로지 API
│   │   ├── ai_routes.py           # AI 모델 API
│   │   ├── clearinghouse_routes.py# Clearing House API
│   │   ├── agent_routes.py        # Agentic AI API
│   │   └── search_routes.py       # 벡터 검색 API
│   │
│   ├── connector/
│   │   ├── control_plane.py       # EDC Control Plane
│   │   └── data_plane.py          # EDC Data Plane (P2P 전송)
│   │
│   ├── identity/
│   │   ├── did.py                 # W3C DID 관리
│   │   └── vc.py                  # Verifiable Credentials
│   │
│   ├── policy/
│   │   └── odrl_engine.py         # ODRL 정책 엔진
│   │
│   ├── contract/
│   │   └── contract_manager.py    # 데이터 계약 관리
│   │
│   ├── metadata/
│   │   └── extractor.py           # DCAT 메타데이터 추출
│   │
│   ├── semantic/
│   │   ├── ontology_mapper.py     # 제조 온톨로지 매핑
│   │   └── vector_search.py       # 의미 기반 검색
│   │
│   ├── ai/
│   │   ├── model_api.py           # 5대 제조 AI 모델
│   │   └── agent.py               # Agentic AI 모듈
│   │
│   ├── clearinghouse/
│   │   └── logger.py              # 해시체인 감사 로그
│   │
│   └── db/
│       ├── models.py              # SQLAlchemy ORM 모델
│       └── database.py            # DB 연결/초기화
│
├── docker/
│   └── Dockerfile.backend
├── docker-compose.yml
└── README.md
```

---

## 빠른 시작

### 방법 1: 직접 실행 (SQLite - 개발용)

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/kmx-platform
cd kmx-platform/backend

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. API 문서 확인
# http://localhost:8000/docs
```

### 방법 2: Docker Compose (운영 권장)

```bash
# 전체 스택 실행 (PostgreSQL + Backend + Provider Connector)
docker-compose up -d

# 로그 확인
docker-compose logs -f kmx-backend

# 중지
docker-compose down
```

### 방법 3: 핵심 로직 테스트 (의존성 없음)

```bash
cd backend
python3 test_core.py
# → 52개 테스트 전체 통과 확인
```

---

## API 명세

### 베이스 URL: `http://localhost:8000/api/v1`

#### 🔐 Identity (DID/VC)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/identity/did` | DID 생성 |
| GET | `/identity/did/{did}` | DID 조회 |
| POST | `/identity/vc` | VC 발급 |
| GET | `/identity/vc/{vc_id}/verify` | VC 검증 |
| POST | `/identity/vc/delegate` | 에이전트 위임 VC 발급 |

#### 🔗 Connector (EDC)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/connector/register` | 커넥터 등록 |
| GET | `/connector/list` | 커넥터 목록 |
| POST | `/connector/negotiate` | 계약 협상 시작 |
| POST | `/connector/data/register` | 데이터셋 등록 |
| POST | `/connector/data/transfer` | 데이터 P2P 전송 |

#### 📋 Policy (ODRL)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/policy/` | 정책 생성 |
| GET | `/policy/` | 정책 목록 |
| POST | `/policy/evaluate` | 정책 평가 |

#### 📝 Contract
| Method | Path | 설명 |
|--------|------|------|
| POST | `/contract/` | 계약 생성 |
| POST | `/contract/{id}/sign` | 계약 서명 |
| GET | `/contract/{id}/verify` | 계약 검증 |

#### 🏷️ Metadata
| Method | Path | 설명 |
|--------|------|------|
| POST | `/metadata/extract` | 메타데이터 추출/저장 |
| GET | `/metadata/` | 데이터셋 카탈로그 |
| POST | `/metadata/ontology/map` | 온톨로지 매핑 |
| GET | `/metadata/ontology/concepts` | 온톨로지 개념 목록 |

#### 🤖 AI
| Method | Path | 설명 |
|--------|------|------|
| POST | `/ai/predict` | AI 예측 실행 |
| GET | `/ai/models` | 모델 목록 |
| GET | `/ai/models/{type}/metadata` | 모델 메타데이터 |
| GET | `/ai/models/{type}/health` | 모델 상태 |

#### 🤖 Agent (Agentic AI)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/agent/initialize` | 에이전트 초기화 |
| POST | `/agent/delegate` | 권한 위임 |
| POST | `/agent/auto-catalog` | 자동 카탈로그 생성 |
| GET | `/agent/health` | 에이전트 상태 |

#### 🔍 Search
| Method | Path | 설명 |
|--------|------|------|
| POST | `/search/datasets` | 자연어 데이터셋 검색 |
| GET | `/search/datasets?q={query}` | 키워드 검색 |
| POST | `/search/ontology` | 온톨로지 기반 검색 |

#### 📊 Clearing House
| Method | Path | 설명 |
|--------|------|------|
| GET | `/clearinghouse/logs` | 전송 로그 조회 |
| GET | `/clearinghouse/verify-chain` | 해시체인 무결성 검증 |
| GET | `/clearinghouse/usage-report` | 사용량 정산 보고서 |

---

## 시나리오 예시: 현대자동차 → 삼성전자 데이터 교환

```bash
BASE="http://localhost:8000/api/v1"

# 1. DID 생성
PROVIDER=$(curl -s -X POST $BASE/identity/did \
  -H "Content-Type: application/json" \
  -d '{"controller":"현대자동차-공급망","entity_type":"connector"}')
PROVIDER_DID=$(echo $PROVIDER | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])")

CONSUMER=$(curl -s -X POST $BASE/identity/did \
  -H "Content-Type: application/json" \
  -d '{"controller":"삼성전자-구미공장","entity_type":"human"}')
CONSUMER_DID=$(echo $CONSUMER | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])")

# 2. 정책 생성
POLICY=$(curl -s -X POST $BASE/policy/ \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"제조 데이터 공유 정책\",
    \"target\": \"supply-chain-dataset-001\",
    \"assigner\": \"$PROVIDER_DID\",
    \"permissions\": [{
      \"action\": \"use\",
      \"constraints\": [
        {\"leftOperand\": \"purpose\", \"operator\": \"eq\", \"rightOperand\": \"manufacturing\"}
      ]
    }],
    \"prohibitions\": [{\"action\": \"distribute\", \"constraints\": []}]
  }")
POLICY_ID=$(echo $POLICY | python3 -c "import sys,json; print(json.load(sys.stdin)['uid'])")

# 3. 커넥터 등록 및 계약 협상 → 데이터 전송
# (이후 negotiate, sign, transfer 순으로 진행)

echo "Provider DID: $PROVIDER_DID"
echo "Policy ID: $POLICY_ID"
```

---

## 표준 준수 사항

| 표준 | 구현 내용 |
|------|-----------|
| **W3C DID Core 1.0** | `did:kmx:` 메서드, DID Document 구조 |
| **W3C VC Data Model 1.1** | VC 발급/검증, Ed25519 서명 |
| **ODRL 2.2** | Permission/Prohibition/Obligation, ODRL JSON-LD |
| **DCAT 2** | 데이터셋 메타데이터, Distribution 구조 |
| **IDS-RAM** | Control/Data Plane 분리, Contract 협상 프로토콜 |
| **ISO 62443** | 산업 사이버보안 (아키텍처 반영) |

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./kmx_platform.db` | DB 연결 문자열 |
| `CONNECTOR_ID` | 자동생성 | 이 인스턴스의 커넥터 ID |

---

## 라이선스

Apache 2.0 — KMX Platform은 오픈소스 레퍼런스 구현입니다.
