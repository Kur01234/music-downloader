class ObjectException(Exception):
    pass


class IsDynamicException(Exception):
    """
    Gets raised, if a dynamic data object tries to perform an action,
    which does not make sense for a dynamic object.
    """
    pass
