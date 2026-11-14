
from app.security.policy import OdinPolicy, Decision


def test_analysis_is_automatic():
    policy = OdinPolicy()

    result = policy.evaluate("analysis")

    assert result.decision == Decision.AUTO
    assert result.approved is True


def test_deletion_requires_approval():
    policy = OdinPolicy()

    result = policy.evaluate("deletion")

    assert result.decision == Decision.APPROVAL_REQUIRED
    assert result.approved is False


def test_unknown_action_is_blocked():
    policy = OdinPolicy()

    result = policy.evaluate("unknown_action")

    assert result.decision == Decision.BLOCKED
    assert result.approved is False


def test_communication_requires_approval():
    policy = OdinPolicy()

    result = policy.evaluate("communication")

    assert result.requires_approval is True
    assert result.approved is False
