from typing import Any


def evaluate_odrl_policy(policy: dict[str, Any], action: str, context: dict[str, Any]) -> dict[str, Any]:
    perms = policy.get("permission", [])
    allowed_action = any(p.get("action") == action for p in perms)
    if not allowed_action:
        return {"allow": False, "reason": "Action not permitted by policy."}

    for c in policy.get("constraint", []):
        left = c.get("leftOperand")
        op = c.get("operator")
        right = c.get("rightOperand")
        value = context.get(left)
        if op == "eq" and value != right:
            return {"allow": False, "reason": f"Constraint failed: {left} must equal {right}"}
        if op == "in" and value not in right:
            return {"allow": False, "reason": f"Constraint failed: {left} not in allowed set"}
    return {"allow": True, "reason": "Policy constraints satisfied."}
from typing import Any


def evaluate_odrl_policy(policy: dict[str, Any], action: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Very small ODRL-like evaluator.
    Expected shape:
    {
      "permission": [{"action": "use", "target": "asset-1"}],
      "constraint": [{"leftOperand": "purpose", "operator": "eq", "rightOperand": "quality"}]
    }
    """
    perms = policy.get("permission", [])
    allowed_action = any(p.get("action") == action for p in perms)
    if not allowed_action:
        return {"allow": False, "reason": "Action not permitted by policy."}

    for c in policy.get("constraint", []):
        left = c.get("leftOperand")
        op = c.get("operator")
        right = c.get("rightOperand")
        value = context.get(left)
        if op == "eq" and value != right:
            return {"allow": False, "reason": f"Constraint failed: {left} must equal {right}"}
        if op == "in" and value not in right:
            return {"allow": False, "reason": f"Constraint failed: {left} not in allowed set"}
    return {"allow": True, "reason": "Policy constraints satisfied."}
