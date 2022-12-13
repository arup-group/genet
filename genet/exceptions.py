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


class MisalignedNodeError(Exception):
    """
    Raised when the Network node is not aligned to geometry of a Network link. E.g. when spliting a link at a node or
    the start/end point of link geometry is different to the location of the node
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


class EmptySpatialTree(Exception):
    """
    Raised when there is no (relevant) data in the Spatial Tree
    """
    pass


class InvalidMaxStableSetProblem(Exception):
    """
    Raised when the maximum stable set to snap PT to the network is not valid and cannot proceed to the solver
    """
    pass


class PartialMaxStableSetProblem(Exception):
    """
    Raised when the maximum stable set to snap PT to the network is partial - some stops found nothing to snap to
    """
    pass


class MalformedAdditionalAttributeError(Exception):
    """
    Raised when additional attributes can not be saved to MATSim network
    """
    pass
