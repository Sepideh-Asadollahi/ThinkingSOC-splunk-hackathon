"""Inventory store errors."""


class InventoryNotFoundError(LookupError):
    pass


class InventoryConflictError(ValueError):
    pass
