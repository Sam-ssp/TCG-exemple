class NotFound(Exception):
    """A card, list or user that does not exist."""


class RuleError(Exception):
    """A request that breaks a validation or collection rule."""
