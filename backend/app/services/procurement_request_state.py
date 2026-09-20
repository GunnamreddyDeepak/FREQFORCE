from typing import Optional

from sqlalchemy.orm import Session

from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)


class InvalidStateTransitionError(ValueError):
    """Raised when an invalid procurement request state transition is attempted."""

    def __init__(
        self,
        current_status: ProcurementRequestStatus,
        target_status: ProcurementRequestStatus,
        allowed_transitions: set[ProcurementRequestStatus],
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        self.allowed_transitions = allowed_transitions
        allowed_names = sorted(s.value for s in allowed_transitions) or ["None (Terminal State)"]
        message = (
            f"Cannot transition procurement request from '{current_status.value}' "
            f"to '{target_status.value}'. Allowed transitions: {', '.join(allowed_names)}"
        )
        super().__init__(message)


VALID_TRANSITIONS: dict[ProcurementRequestStatus, set[ProcurementRequestStatus]] = {
    ProcurementRequestStatus.REQUESTED: {
        ProcurementRequestStatus.ELIGIBILITY_CHECKED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.ELIGIBILITY_CHECKED: {
        ProcurementRequestStatus.CENTRE_RECOMMENDED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.CENTRE_RECOMMENDED: {
        ProcurementRequestStatus.SLOT_CONFIRMED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.SLOT_CONFIRMED: {
        ProcurementRequestStatus.TOKEN_GENERATED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.TOKEN_GENERATED: {
        ProcurementRequestStatus.CHECKED_IN,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.CHECKED_IN: {
        ProcurementRequestStatus.WEIGHED,
        ProcurementRequestStatus.WEIGHMENT_EXCEPTION,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.WEIGHED: {
        ProcurementRequestStatus.QUALITY_TESTED,
        ProcurementRequestStatus.QUALITY_EXCEPTION,
    },
    ProcurementRequestStatus.QUALITY_TESTED: {
        ProcurementRequestStatus.BILLED,
    },
    ProcurementRequestStatus.BILLED: {
        ProcurementRequestStatus.PAYMENT_INITIATED,
    },
    ProcurementRequestStatus.PAYMENT_INITIATED: {
        ProcurementRequestStatus.PAYMENT_COMPLETED,
        ProcurementRequestStatus.PAYMENT_FAILED,
    },
    ProcurementRequestStatus.PAYMENT_FAILED: {
        ProcurementRequestStatus.PAYMENT_INITIATED,
    },
    ProcurementRequestStatus.WEIGHMENT_EXCEPTION: {
        ProcurementRequestStatus.WEIGHED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.QUALITY_EXCEPTION: {
        ProcurementRequestStatus.QUALITY_TESTED,
        ProcurementRequestStatus.CANCELLED,
    },
    ProcurementRequestStatus.PAYMENT_COMPLETED: set(),
    ProcurementRequestStatus.CANCELLED: set(),
}

TERMINAL_STATES: set[ProcurementRequestStatus] = {
    ProcurementRequestStatus.PAYMENT_COMPLETED,
    ProcurementRequestStatus.CANCELLED,
}

EXCEPTIONAL_STATES: set[ProcurementRequestStatus] = {
    ProcurementRequestStatus.CANCELLED,
    ProcurementRequestStatus.QUALITY_EXCEPTION,
    ProcurementRequestStatus.WEIGHMENT_EXCEPTION,
    ProcurementRequestStatus.PAYMENT_FAILED,
}


def normalize_status(
    status: str | ProcurementRequestStatus,
) -> ProcurementRequestStatus:
    """Normalize input status to a ProcurementRequestStatus enum."""
    if isinstance(status, ProcurementRequestStatus):
        return status
    try:
        return ProcurementRequestStatus(status)
    except ValueError as exc:
        raise ValueError(
            f"Invalid procurement request status: '{status}'"
        ) from exc


def get_allowed_transitions(
    status: str | ProcurementRequestStatus,
) -> set[ProcurementRequestStatus]:
    """Return the set of valid next states from the given status."""
    current = normalize_status(status)
    return set(VALID_TRANSITIONS.get(current, set()))


def can_transition(
    current_status: str | ProcurementRequestStatus,
    target_status: str | ProcurementRequestStatus,
) -> bool:
    """Check whether a transition between two statuses is permitted."""
    try:
        current = normalize_status(current_status)
        target = normalize_status(target_status)
    except ValueError:
        return False
    return target in VALID_TRANSITIONS.get(current, set())


def validate_transition(
    current_status: str | ProcurementRequestStatus,
    target_status: str | ProcurementRequestStatus,
) -> None:
    """Validate a transition between two statuses or raise InvalidStateTransitionError."""
    current = normalize_status(current_status)
    target = normalize_status(target_status)
    allowed = VALID_TRANSITIONS.get(current, set())

    if target not in allowed:
        raise InvalidStateTransitionError(
            current_status=current,
            target_status=target,
            allowed_transitions=allowed,
        )


def is_terminal_state(
    status: str | ProcurementRequestStatus,
) -> bool:
    """Return True if the status is a terminal state."""
    current = normalize_status(status)
    return current in TERMINAL_STATES


def is_exceptional_state(
    status: str | ProcurementRequestStatus,
) -> bool:
    """Return True if the status is an exceptional state."""
    current = normalize_status(status)
    return current in EXCEPTIONAL_STATES


def transition_procurement_request(
    procurement_request: ProcurementRequest,
    target_status: str | ProcurementRequestStatus,
    db: Optional[Session] = None,
) -> ProcurementRequest:
    """Perform a validated status transition on a procurement request.

    Raises InvalidStateTransitionError if the transition is not allowed.
    If a database session is provided, the updated entity is flushed.
    """
    validate_transition(
        current_status=procurement_request.status,
        target_status=target_status,
    )

    target_enum = normalize_status(target_status)
    procurement_request.status = target_enum.value

    if db is not None:
        db.add(procurement_request)
        db.flush()

    return procurement_request
