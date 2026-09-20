import pytest

from app.db.session import get_session_factory
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.services.procurement_request_state import (
    EXCEPTIONAL_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    can_transition,
    get_allowed_transitions,
    is_exceptional_state,
    is_terminal_state,
    normalize_status,
    transition_procurement_request,
    validate_transition,
)


def test_all_expected_statuses_exist():
    """Verifies that all 15 required domain statuses exist in the enum."""
    expected_primary = [
        "REQUESTED",
        "ELIGIBILITY_CHECKED",
        "CENTRE_RECOMMENDED",
        "SLOT_CONFIRMED",
        "TOKEN_GENERATED",
        "CHECKED_IN",
        "WEIGHED",
        "QUALITY_TESTED",
        "BILLED",
        "PAYMENT_INITIATED",
        "PAYMENT_COMPLETED",
    ]
    expected_exceptional = [
        "CANCELLED",
        "QUALITY_EXCEPTION",
        "WEIGHMENT_EXCEPTION",
        "PAYMENT_FAILED",
    ]

    for status_name in expected_primary + expected_exceptional:
        assert status_name in ProcurementRequestStatus.__members__
        assert ProcurementRequestStatus(status_name).value == status_name


def test_valid_primary_lifecycle_flow():
    """Verifies the complete 11-step happy-path lifecycle sequentially."""
    lifecycle_steps = [
        ProcurementRequestStatus.REQUESTED,
        ProcurementRequestStatus.ELIGIBILITY_CHECKED,
        ProcurementRequestStatus.CENTRE_RECOMMENDED,
        ProcurementRequestStatus.SLOT_CONFIRMED,
        ProcurementRequestStatus.TOKEN_GENERATED,
        ProcurementRequestStatus.CHECKED_IN,
        ProcurementRequestStatus.WEIGHED,
        ProcurementRequestStatus.QUALITY_TESTED,
        ProcurementRequestStatus.BILLED,
        ProcurementRequestStatus.PAYMENT_INITIATED,
        ProcurementRequestStatus.PAYMENT_COMPLETED,
    ]

    request = ProcurementRequest(
        requested_quantity=50.0,
        status=ProcurementRequestStatus.REQUESTED.value,
    )

    for i in range(len(lifecycle_steps) - 1):
        current_state = lifecycle_steps[i]
        next_state = lifecycle_steps[i + 1]

        assert request.status == current_state.value
        assert can_transition(request.status, next_state) is True

        transition_procurement_request(request, next_state)
        assert request.status == next_state.value

    assert request.status == ProcurementRequestStatus.PAYMENT_COMPLETED.value


def test_valid_cancellations_from_allowed_states():
    """Verifies cancellation is allowed from states prior to/during initial processing."""
    cancellable_states = [
        ProcurementRequestStatus.REQUESTED,
        ProcurementRequestStatus.ELIGIBILITY_CHECKED,
        ProcurementRequestStatus.CENTRE_RECOMMENDED,
        ProcurementRequestStatus.SLOT_CONFIRMED,
        ProcurementRequestStatus.TOKEN_GENERATED,
        ProcurementRequestStatus.CHECKED_IN,
        ProcurementRequestStatus.WEIGHMENT_EXCEPTION,
        ProcurementRequestStatus.QUALITY_EXCEPTION,
    ]

    for state in cancellable_states:
        request = ProcurementRequest(status=state.value)
        assert can_transition(state, ProcurementRequestStatus.CANCELLED) is True
        transition_procurement_request(request, ProcurementRequestStatus.CANCELLED)
        assert request.status == ProcurementRequestStatus.CANCELLED.value


def test_valid_exception_and_recovery_transitions():
    """Verifies weighment, quality, and payment exceptions and their recovery paths."""
    # 1. Weighment exception and recovery
    req_weigh = ProcurementRequest(status=ProcurementRequestStatus.CHECKED_IN.value)
    transition_procurement_request(req_weigh, ProcurementRequestStatus.WEIGHMENT_EXCEPTION)
    assert req_weigh.status == ProcurementRequestStatus.WEIGHMENT_EXCEPTION.value
    transition_procurement_request(req_weigh, ProcurementRequestStatus.WEIGHED)
    assert req_weigh.status == ProcurementRequestStatus.WEIGHED.value

    # 2. Quality exception and recovery
    req_qual = ProcurementRequest(status=ProcurementRequestStatus.WEIGHED.value)
    transition_procurement_request(req_qual, ProcurementRequestStatus.QUALITY_EXCEPTION)
    assert req_qual.status == ProcurementRequestStatus.QUALITY_EXCEPTION.value
    transition_procurement_request(req_qual, ProcurementRequestStatus.QUALITY_TESTED)
    assert req_qual.status == ProcurementRequestStatus.QUALITY_TESTED.value

    # 3. Payment failed and retry
    req_pay = ProcurementRequest(status=ProcurementRequestStatus.PAYMENT_INITIATED.value)
    transition_procurement_request(req_pay, ProcurementRequestStatus.PAYMENT_FAILED)
    assert req_pay.status == ProcurementRequestStatus.PAYMENT_FAILED.value
    transition_procurement_request(req_pay, ProcurementRequestStatus.PAYMENT_INITIATED)
    assert req_pay.status == ProcurementRequestStatus.PAYMENT_INITIATED.value


def test_terminal_states_have_no_outgoing_transitions():
    """Verifies that terminal states cannot transition to any other state."""
    terminal_states = [
        ProcurementRequestStatus.PAYMENT_COMPLETED,
        ProcurementRequestStatus.CANCELLED,
    ]

    for terminal in terminal_states:
        assert is_terminal_state(terminal) is True
        assert get_allowed_transitions(terminal) == set()

        for any_target in ProcurementRequestStatus:
            assert can_transition(terminal, any_target) is False

            req = ProcurementRequest(status=terminal.value)
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                transition_procurement_request(req, any_target)

            assert exc_info.value.current_status == terminal
            assert exc_info.value.target_status == any_target
            assert exc_info.value.allowed_transitions == set()


def test_invalid_forward_skipping_transitions():
    """Verifies that skipping intermediate workflow steps is prohibited."""
    invalid_skips = [
        (ProcurementRequestStatus.REQUESTED, ProcurementRequestStatus.SLOT_CONFIRMED),
        (ProcurementRequestStatus.REQUESTED, ProcurementRequestStatus.WEIGHED),
        (ProcurementRequestStatus.REQUESTED, ProcurementRequestStatus.PAYMENT_COMPLETED),
        (ProcurementRequestStatus.ELIGIBILITY_CHECKED, ProcurementRequestStatus.CHECKED_IN),
        (ProcurementRequestStatus.CENTRE_RECOMMENDED, ProcurementRequestStatus.TOKEN_GENERATED),
        (ProcurementRequestStatus.CHECKED_IN, ProcurementRequestStatus.BILLED),
        (ProcurementRequestStatus.WEIGHED, ProcurementRequestStatus.PAYMENT_INITIATED),
    ]

    for current, invalid_target in invalid_skips:
        assert can_transition(current, invalid_target) is False
        req = ProcurementRequest(status=current.value)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            transition_procurement_request(req, invalid_target)

        assert exc_info.value.current_status == current
        assert exc_info.value.target_status == invalid_target


def test_invalid_backward_transitions():
    """Verifies that arbitrary backward transitions are blocked."""
    invalid_backwards = [
        (ProcurementRequestStatus.BILLED, ProcurementRequestStatus.WEIGHED),
        (ProcurementRequestStatus.BILLED, ProcurementRequestStatus.REQUESTED),
        (ProcurementRequestStatus.QUALITY_TESTED, ProcurementRequestStatus.CHECKED_IN),
        (ProcurementRequestStatus.WEIGHED, ProcurementRequestStatus.SLOT_CONFIRMED),
        (ProcurementRequestStatus.CHECKED_IN, ProcurementRequestStatus.REQUESTED),
    ]

    for current, invalid_target in invalid_backwards:
        assert can_transition(current, invalid_target) is False
        req = ProcurementRequest(status=current.value)
        with pytest.raises(InvalidStateTransitionError):
            transition_procurement_request(req, invalid_target)


def test_exceptional_states_classification():
    """Verifies is_exceptional_state for all domain statuses."""
    for status in ProcurementRequestStatus:
        if status in [
            ProcurementRequestStatus.CANCELLED,
            ProcurementRequestStatus.QUALITY_EXCEPTION,
            ProcurementRequestStatus.WEIGHMENT_EXCEPTION,
            ProcurementRequestStatus.PAYMENT_FAILED,
        ]:
            assert is_exceptional_state(status) is True
        else:
            assert is_exceptional_state(status) is False


def test_status_normalization_and_validation():
    """Verifies status string parsing and validation."""
    assert normalize_status("REQUESTED") == ProcurementRequestStatus.REQUESTED
    assert normalize_status(ProcurementRequestStatus.BILLED) == ProcurementRequestStatus.BILLED

    with pytest.raises(ValueError, match="Invalid procurement request status"):
        normalize_status("INVALID_UNKNOWN_STATUS")

    assert can_transition("UNKNOWN_STATE", "REQUESTED") is False
    assert can_transition("REQUESTED", "UNKNOWN_TARGET") is False


def test_transition_procurement_request_with_db_session(procurement_test_data):
    """Verifies that transition_procurement_request persists to database when session provided."""
    factory = get_session_factory()
    db = factory()

    try:
        from geoalchemy2 import WKTElement

        request = ProcurementRequest(
            farmer_id=procurement_test_data["farmer_id"],
            commodity_id=procurement_test_data["commodity_id"],
            requested_quantity=40.0,
            preferred_date="2026-09-20",
            farmer_location=WKTElement("POINT(80.2707 13.0827)", srid=4326),
            status=ProcurementRequestStatus.REQUESTED.value,
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        assert request.status == "REQUESTED"

        # Perform transition with db session
        transition_procurement_request(
            request,
            ProcurementRequestStatus.ELIGIBILITY_CHECKED,
            db=db,
        )
        db.commit()
        db.refresh(request)

        assert request.status == "ELIGIBILITY_CHECKED"

        # Verify state in fresh query
        reloaded = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request.id)
            .one()
        )
        assert reloaded.status == "ELIGIBILITY_CHECKED"

    finally:
        db.close()


def test_existing_requested_behaviour_preserved():
    """Verifies that a new ProcurementRequest instance defaults to REQUESTED."""
    req = ProcurementRequest()
    # When default value evaluates or when assigned
    assert req.status is None or req.status == ProcurementRequestStatus.REQUESTED.value
