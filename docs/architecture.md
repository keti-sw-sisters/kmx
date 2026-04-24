# KMX Manufacturing-X 레퍼런스 아키텍처

## 1) 전체 레이어

1. Data Space Layer  
   - EDC 유사 구조로 Control Plane/ Data Plane 분리  
   - Control Plane: 자산 등록, 계약 참조, 메타데이터 관리  
   - Data Plane: P2P 데이터 전송 이벤트 처리 (중앙 데이터 저장 없음)

2. Identity & Governance Layer  
   - W3C DID/VC 기반 신원 생성 및 검증  
   - Agentic Identity: 사용자 DID -> 에이전트 DID 권한 위임 토큰  
   - ODRL 유사 정책 평가 엔진  
   - 계약(Contract) 생성/서명/검증

3. AI Layer  
   - 5대 제조 AI 모델 API (`/ai/{model}/predict`)  
   - 로컬 Ollama 호출 + 오프라인 fallback  
   - 표준 인터페이스: `/predict` 계열, `/metadata`, `/health`

4. Data Intelligence Layer  
   - 메타데이터 자동 추출  
   - 온톨로지 매핑(DCAT 친화 메타구조에 연결 가능한 개념 URI)  
   - Chroma Vector DB 기반 검색 (RAG 베이스)

## 2) IDS-RAM / DCAT / ODRL 반영 포인트

- IDS-RAM: 커넥터 중심의 신뢰 데이터 교환(자산/계약/정책/전송 이벤트 분리)
- DCAT: 자산 메타데이터를 카탈로그화 가능한 JSON 구조로 보관
- ODRL: permission + constraint(목적 제한 등) 평가
- DID/VC: 주체 인증 및 위임 토큰 발급
- Cross-Certification: VC 검증 + 계약 서명 검증 + Clearing House 공증 로그 조합으로 설계

## 3) 텍스트 데이터 흐름 다이어그램

```text
[Provider User DID]
   -> issue VC
   -> register asset (Control Plane)
   -> create contract + ODRL policy

[Consumer User DID] --delegate--> [Agent DID]
   -> request transfer with contract
   -> policy evaluation
   -> data transfer (Data Plane P2P)
   -> transfer hash/signature generated
   -> Clearing House notarization + DuckDB event record
   -> usage settlement

[Agentic AI]
   -> metadata extraction
   -> ontology mapping
   -> catalog draft/API draft generation
   -> vector indexing + semantic search

[AI Runtime on Edge]
   -> /ai/{model}/predict
   -> local ollama inference (or fallback)
```

## 4) 모듈 역할

- `backend/connector`: 연합 커넥터 샘플, 제어/데이터 평면 분리
- `backend/identity`: DID 생성, VC 발급/검증, 위임 토큰
- `backend/policy`: ODRL 정책 평가
- `backend/contract`: 계약 생성/검증
- `backend/metadata`: 메타데이터 추출
- `backend/semantic`: 온톨로지 매핑, 벡터 인덱싱/검색
- `backend/ai`: 로컬 AI 모델 래퍼
- `backend/clearinghouse`: 전송 공증 로그, 정산

