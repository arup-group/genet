class ScheduleElementGraphSchemaError(Exception):
    """
    Raised when the graph which represents a Schedule or any of its' sub elements is missing data or is not arranged
    correctly
    """
    pass


class NetworkSchemaError(Exception):
    """
    Raised when the Network or any of its' elements is missing data or is not arranged correctly
    """
    pass


class RouteInitialisationError(Exception):
    """
    Raised when a genet.Route cannot be instantiated
    """
    pass


class RouteIndexError(Exception):
    """
    Raised in case of Route indexing inconsistency
    """
    pass


class ServiceInitialisationError(Exception):
    """
    Raised when a genet.Service cannot be instantiated
    """
    pass


class ServiceIndexError(Exception):
    """
    Raised in case of Service indexing inconsistency
    """
    pass


class ScheduleInitialisationError(Exception):
    """
    Raised when a genet.Schedule cannot be instantiated
    """
    pass


class ConflictingStopData(Exception):
    """
    Raised when two elements share Stop IDs but their data does not match
    """
    pass


class UndefinedCoordinateSystemError(Exception):
    """
    Raised when an object requires a coordinate system
    """
    pass


class StopIndexError(Exception):
    """
    Raised in case of Stop indexing inconsistency
    """
    pass


class InconsistentVehicleModeError(Exception):
    """
    Raised when vehicles are shared between Routes with different modes
    """
    pass
