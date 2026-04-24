"""
ODRL (Open Digital Rights Language) 정책 엔진
W3C ODRL Information Model 2.2 기반
데이터 사용 권한/금지/의무를 정책으로 관리
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import ODRLPolicy
import logging

logger = logging.getLogger(__name__)


class PolicyEvaluationResult:
    def __init__(self, permitted: bool, reason: str, matched_rules: list = None):
        self.permitted = permitted
        self.reason = reason
        self.matched_rules = matched_rules or []


class ODRLEngine:
    """
    ODRL 정책 엔진
    - Permission: 허용된 행위
    - Prohibition: 금지된 행위  
    - Obligation: 의무 사항
    """

    ACTIONS = {
        "use": "데이터 사용",
        "read": "데이터 읽기",
        "write": "데이터 쓰기",
        "distribute": "데이터 배포",
        "derive": "파생 데이터 생성",
        "anonymize": "익명화",
        "aggregate": "집계",
        "delete": "삭제",
    }

    async def create_policy(
        self,
        db: AsyncSession,
        title: str,
        target: str,
        assigner: str,
        permissions: list,
        prohibitions: list = None,
        obligations: list = None,
        assignee: Optional[str] = None,
        policy_type: str = "Offer",
    ) -> dict:
        """
        ODRL 정책 생성
        
        Example permissions:
        [
          {
            "action": "use",
            "constraints": [
              {"leftOperand": "dateTime", "operator": "lt", "rightOperand": "2025-12-31"},
              {"leftOperand": "purpose", "operator": "eq", "rightOperand": "manufacturing"}
            ]
          }
        ]
        """
        policy_id = f"policy:kmx:{uuid.uuid4().hex[:16]}"

        policy_record = ODRLPolicy(
            policy_id=policy_id,
            title=title,
            policy_type=policy_type,
            target=target,
            assigner=assigner,
            assignee=assignee,
            permissions=permissions or [],
            prohibitions=prohibitions or [],
            obligations=obligations or [],
        )
        db.add(policy_record)
        await db.flush()

        odrl_doc = self._build_odrl_document(policy_record)
        logger.info(f"✅ 정책 생성: {policy_id}")
        return odrl_doc

    def _build_odrl_document(self, policy: ODRLPolicy) -> dict:
        """ODRL JSON-LD 문서 생성"""
        doc = {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@type": policy.policy_type,
            "uid": policy.policy_id,
            "profile": "https://kmx.kr/odrl/profile/manufacturing",
            "title": policy.title,
            "target": policy.target,
            "assigner": {"uid": policy.assigner},
            "created": policy.created_at.isoformat() + "Z",
        }

        if policy.assignee:
            doc["assignee"] = {"uid": policy.assignee}

        if policy.permissions:
            doc["permission"] = [
                self._build_rule(p) for p in policy.permissions
            ]

        if policy.prohibitions:
            doc["prohibition"] = [
                self._build_rule(p) for p in policy.prohibitions
            ]

        if policy.obligations:
            doc["obligation"] = [
                self._build_rule(p) for p in policy.obligations
            ]

        return doc

    def _build_rule(self, rule: dict) -> dict:
        """규칙 ODRL 포맷 변환"""
        result = {"action": rule.get("action", "use")}
        constraints = rule.get("constraints", [])
        if constraints:
            result["constraint"] = [
                {
                    "leftOperand": c["leftOperand"],
                    "operator": c["operator"],
                    "rightOperand": c["rightOperand"]
                }
                for c in constraints
            ]
        return result

    async def evaluate_policy(
        self,
        db: AsyncSession,
        policy_id: str,
        requester_did: str,
        action: str,
        context: dict = None,
    ) -> PolicyEvaluationResult:
        """
        정책 평가 - 요청이 정책에 부합하는지 검사
        
        Args:
            policy_id: 정책 ID
            requester_did: 요청자 DID
            action: 수행하려는 행위 (use, read, write, ...)
            context: 평가 컨텍스트 (시간, 목적, 위치 등)
        """
        result = await db.execute(
            select(ODRLPolicy).where(
                ODRLPolicy.policy_id == policy_id,
                ODRLPolicy.active == True
            )
        )
        policy = result.scalar_one_or_none()

        if not policy:
            return PolicyEvaluationResult(False, "정책을 찾을 수 없습니다")

        context = context or {}
        matched_rules = []

        # 1. Prohibition 먼저 검사 (금지가 우선)
        for prohibition in (policy.prohibitions or []):
            if prohibition.get("action") == action:
                if self._check_constraints(prohibition.get("constraints", []), requester_did, context):
                    return PolicyEvaluationResult(
                        False,
                        f"행위 '{action}'이 정책에 의해 금지되어 있습니다",
                        [prohibition]
                    )

        # 2. Assignee 검사
        if policy.assignee and policy.assignee != requester_did:
            return PolicyEvaluationResult(
                False,
                f"정책이 지정된 수신자에게만 허용됩니다: {policy.assignee}"
            )

        # 3. Permission 검사
        for permission in (policy.permissions or []):
            if permission.get("action") == action or permission.get("action") == "use":
                constraints_ok = self._check_constraints(
                    permission.get("constraints", []),
                    requester_did,
                    context
                )
                if constraints_ok:
                    matched_rules.append(permission)

        if matched_rules:
            return PolicyEvaluationResult(
                True,
                f"행위 '{action}'이 정책에 의해 허용됩니다",
                matched_rules
            )

        return PolicyEvaluationResult(
            False,
            f"행위 '{action}'에 대한 허용 정책이 없습니다"
        )

    def _check_constraints(self, constraints: list, requester_did: str, context: dict) -> bool:
        """제약 조건 검사"""
        if not constraints:
            return True

        for constraint in constraints:
            left = constraint.get("leftOperand")
            operator = constraint.get("operator")
            right = constraint.get("rightOperand")

            if left == "dateTime":
                now = datetime.utcnow().isoformat()
                if operator == "lt" and not (now < right):
                    return False
                elif operator == "gt" and not (now > right):
                    return False

            elif left == "purpose":
                purpose = context.get("purpose", "")
                if operator == "eq" and purpose != right:
                    return False

            elif left == "requester":
                if operator == "eq" and requester_did != right:
                    return False

            elif left == "count":
                usage_count = context.get("usage_count", 0)
                if operator == "lteq" and usage_count > int(right):
                    return False

        return True

    async def get_policy(self, db: AsyncSession, policy_id: str) -> Optional[dict]:
        """정책 조회"""
        result = await db.execute(select(ODRLPolicy).where(ODRLPolicy.policy_id == policy_id))
        policy = result.scalar_one_or_none()
        if not policy:
            return None
        return self._build_odrl_document(policy)

    async def list_policies(self, db: AsyncSession) -> list:
        """정책 목록"""
        result = await db.execute(select(ODRLPolicy).where(ODRLPolicy.active == True))
        policies = result.scalars().all()
        return [
            {
                "policy_id": p.policy_id,
                "title": p.title,
                "policy_type": p.policy_type,
                "target": p.target,
                "assigner": p.assigner,
                "created_at": p.created_at.isoformat(),
            }
            for p in policies
        ]


# 싱글톤
odrl_engine = ODRLEngine()
