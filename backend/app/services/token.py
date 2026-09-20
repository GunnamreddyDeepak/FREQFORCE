from datetime import date
from uuid import UUID

from sqlalchemy import insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.centre_slot import CentreSlot
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.token import Token, TokenStatus
from app.models.token_sequence import TokenSequence


def allocate_token(
    db: Session,
    centre: ProcurementCentre,
    slot: CentreSlot,
    procurement_request: ProcurementRequest,
) -> Token:
    """Atomically allocate a monotonic daily token for a confirmed slot booking.
    Uses INSERT ON CONFLICT DO NOTHING + SELECT FOR UPDATE on token_sequences
    to guarantee concurrency-safe, gapless, strictly monotonic sequential numbering.
    """
    token_date = slot.slot_date

    # 1. Insert sequence counter row if not already present
    insert_stmt = (
        pg_insert(TokenSequence)
        .values(
            centre_id=centre.id,
            token_date=token_date,
            next_sequence=1,
        )
        .on_conflict_do_nothing(
            constraint="uq_token_sequence_centre_date"
        )
    )
    db.execute(insert_stmt)
    db.flush()

    # 2. Lock the sequence counter row exclusively
    seq_row = (
        db.query(TokenSequence)
        .filter(
            TokenSequence.centre_id == centre.id,
            TokenSequence.token_date == token_date,
        )
        .with_for_update()
        .first()
    )

    if seq_row is None:
        raise RuntimeError("Failed to acquire token sequence lock")

    # 3. Read and increment sequence
    allocated_seq = seq_row.next_sequence
    seq_row.next_sequence = allocated_seq + 1
    db.add(seq_row)
    db.flush()

    # 4. Generate formatted token number
    token_number = f"KQ-{centre.centre_code}-{token_date.strftime('%Y%m%d')}-{allocated_seq:03d}"

    # 5. Create and persist Token entity
    token = Token(
        token_number=token_number,
        procurement_request_id=procurement_request.id,
        centre_id=centre.id,
        slot_id=slot.id,
        token_date=token_date,
        status=TokenStatus.ACTIVE.value,
    )
    db.add(token)
    db.flush()

    return token
