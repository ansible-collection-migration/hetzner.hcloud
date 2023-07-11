try:
    from dateutil.parser import isoparse
except ImportError:
    isoparse = None

from .._exceptions import HCloudException
from ..core.domain import BaseDomain


class Action(BaseDomain):
    """Action Domain

    :param id: int ID of an action
    :param command: Command executed in the action
    :param status: Status of the action
    :param progress: Progress of action in percent
    :param started: Point in time when the action was started
    :param datetime,None finished: Point in time when the action was finished. Only set if the action is finished otherwise None
    :param resources: Resources the action relates to
    :param error: Error message for the action if error occurred, otherwise None.
    """

    STATUS_RUNNING = "running"
    """Action Status running"""
    STATUS_SUCCESS = "success"
    """Action Status success"""
    STATUS_ERROR = "error"
    """Action Status error"""

    __slots__ = (
        "id",
        "command",
        "status",
        "progress",
        "resources",
        "error",
        "started",
        "finished",
    )

    def __init__(
        self,
        id,
        command=None,
        status=None,
        progress=None,
        started=None,
        finished=None,
        resources=None,
        error=None,
    ):
        self.id = id
        self.command = command

        self.status = status
        self.progress = progress
        self.started = isoparse(started) if started else None
        self.finished = isoparse(finished) if finished else None
        self.resources = resources
        self.error = error


class ActionException(HCloudException):
    """A generic action exception"""

    def __init__(self, action):
        self.action = action


class ActionFailedException(ActionException):
    """The Action you were waiting for failed"""


class ActionTimeoutException(ActionException):
    """The Action you were waiting for timed out"""
