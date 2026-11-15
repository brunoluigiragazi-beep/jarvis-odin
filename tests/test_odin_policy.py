
from app.security.policy import OdinPolicy, Decision


def test_analysis_is_automatic():
    policy = OdinPolicy()

    result = policy.evaluate("analysis")

    assert result.decision == Decision.AUTO
    assert result.requires_approval is False
    assert not hasattr(result, "approved")


def test_read_is_automatic():
    policy = OdinPolicy()

    result = policy.evaluate("read")

    assert result.decision == Decision.AUTO
    assert result.requires_approval is False


def test_deletion_requires_approval():
    policy = OdinPolicy()

    result = policy.evaluate("deletion")

    assert result.decision == Decision.APPROVAL_REQUIRED
    assert result.requires_approval is True


def test_unknown_action_is_blocked():
    policy = OdinPolicy()

    result = policy.evaluate("unknown_action")

    assert result.decision == Decision.BLOCKED
    assert result.requires_approval is True


def test_communication_requires_approval():
    policy = OdinPolicy()

    result = policy.evaluate("communication")

    assert result.decision == Decision.APPROVAL_REQUIRED
    assert result.requires_approval is True


def test_action_type_is_normalized():
    policy = OdinPolicy()

    result = policy.evaluate("  ANALYSIS  ")

    assert result.action_type == "analysis"
    assert result.decision == Decision.AUTO
