"""Public feedback failures without SDK details."""


class FeedbackForbidden(Exception):
    """Invalid or expired feedback capability."""


class FeedbackUnavailable(Exception):
    """Feedback storage could not acknowledge a write."""


class FeedbackTimeout(Exception):
    """Feedback storage did not acknowledge within the deadline."""
