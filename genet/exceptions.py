class ScheduleElementGraphSchemaError(Exception):
    """
    Raised when the graph which represents a Schedule or any of its' sub elements is missing data or is not arranged
    correctly
    """
    pass


class RouteInitialisationError(Exception):
    """
    Raised when a genet.Route cannot be instantiated
    """
    pass


class ServiceInitialisationError(Exception):
    """
    Raised when a genet.Service cannot be instantiated
    """
    pass


class ScheduleInitialisationError(Exception):
    """
    Raised when a genet.Schedule cannot be instantiated
    """
    pass


class UndefinedCoordinateSystemError(Exception):
    """
    Raised when an object requires a coordinate system
    """
    pass
