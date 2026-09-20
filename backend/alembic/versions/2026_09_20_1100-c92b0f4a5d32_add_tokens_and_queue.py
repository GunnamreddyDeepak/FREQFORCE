"""add token sequences tokens and queue entries

Revision ID: c92b0f4a5d32
Revises: b81a9f3e4c21
Create Date: 2026-09-20 11:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c92b0f4a5d32'
down_revision: Union[str, None] = 'b81a9f3e4c21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. token_sequences table
    op.create_table(
        'token_sequences',
        sa.Column('id', sa.Uuid(), nullable=False, comment='Authoritative token sequence UUID'),
        sa.Column('centre_id', sa.Uuid(), nullable=False, comment='Procurement centre UUID'),
        sa.Column('token_date', sa.Date(), nullable=False, comment='Date for which this sequence applies'),
        sa.Column('next_sequence', sa.Integer(), server_default='1', nullable=False, comment='Next sequence number to allocate'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Sequence record creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Sequence record last update timestamp (UTC)'),
        sa.ForeignKeyConstraint(['centre_id'], ['procurement_centres.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('centre_id', 'token_date', name='uq_token_sequence_centre_date'),
        sa.CheckConstraint('next_sequence >= 1', name='ck_token_sequence_next_seq'),
    )
    op.create_index(op.f('ix_token_sequences_centre_id'), 'token_sequences', ['centre_id'], unique=False)
    op.create_index(op.f('ix_token_sequences_token_date'), 'token_sequences', ['token_date'], unique=False)

    # 2. tokens table
    op.create_table(
        'tokens',
        sa.Column('id', sa.Uuid(), nullable=False, comment='Authoritative token UUID'),
        sa.Column('token_number', sa.String(length=32), nullable=False, comment='Human-readable token number (e.g. KQ-KQM-20260925-001)'),
        sa.Column('procurement_request_id', sa.Uuid(), nullable=False, comment='1:1 procurement request UUID'),
        sa.Column('centre_id', sa.Uuid(), nullable=False, comment='Procurement centre UUID'),
        sa.Column('slot_id', sa.Uuid(), nullable=False, comment='Confirmed centre slot UUID'),
        sa.Column('token_date', sa.Date(), nullable=False, comment='Scheduled appointment date'),
        sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=False, comment='Token status (ACTIVE, USED, CANCELLED, EXPIRED)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Token creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Token last update timestamp (UTC)'),
        sa.ForeignKeyConstraint(['centre_id'], ['procurement_centres.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['procurement_request_id'], ['procurement_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['slot_id'], ['centre_slots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('centre_id', 'token_date', 'token_number', name='uq_tokens_centre_date_number'),
        sa.UniqueConstraint('procurement_request_id', name='uq_tokens_procurement_request'),
    )
    op.create_index(op.f('ix_tokens_centre_id'), 'tokens', ['centre_id'], unique=False)
    op.create_index(op.f('ix_tokens_procurement_request_id'), 'tokens', ['procurement_request_id'], unique=True)
    op.create_index(op.f('ix_tokens_slot_id'), 'tokens', ['slot_id'], unique=False)
    op.create_index(op.f('ix_tokens_status'), 'tokens', ['status'], unique=False)
    op.create_index(op.f('ix_tokens_token_date'), 'tokens', ['token_date'], unique=False)
    op.create_index(op.f('ix_tokens_token_number'), 'tokens', ['token_number'], unique=False)

    # 3. queue_entries table
    op.create_table(
        'queue_entries',
        sa.Column('id', sa.Uuid(), nullable=False, comment='Authoritative queue entry UUID'),
        sa.Column('token_id', sa.Uuid(), nullable=False, comment='Verified arrival token UUID'),
        sa.Column('procurement_request_id', sa.Uuid(), nullable=False, comment='1:1 procurement request UUID'),
        sa.Column('centre_id', sa.Uuid(), nullable=False, comment='Procurement centre UUID'),
        sa.Column('slot_id', sa.Uuid(), nullable=False, comment='Confirmed slot UUID'),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=False, comment='Gate check-in timestamp (UTC)'),
        sa.Column('is_late', sa.Boolean(), server_default='false', nullable=False, comment='True if check-in occurred after slot end time'),
        sa.Column('vehicle_number', sa.String(length=32), nullable=True, comment='Vehicle number at check-in'),
        sa.Column('status', sa.String(length=32), server_default='WAITING', nullable=False, comment='Queue status (WAITING, CALLED, PROCESSING, COMPLETED, NO_SHOW, CANCELLED)'),
        sa.Column('called_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when farmer was called to desk/bay (UTC)'),
        sa.Column('service_start_time', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when intake/weighment service started (UTC)'),
        sa.Column('service_end_time', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when intake/weighment service ended (UTC)'),
        sa.Column('counter_or_bay', sa.String(length=32), nullable=True, comment='Assigned desk or weighbridge bay'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Queue record creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Queue record last update timestamp (UTC)'),
        sa.ForeignKeyConstraint(['centre_id'], ['procurement_centres.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['procurement_request_id'], ['procurement_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['slot_id'], ['centre_slots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['token_id'], ['tokens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('procurement_request_id', name='uq_queue_entries_procurement_request'),
        sa.UniqueConstraint('token_id', name='uq_queue_entries_token'),
    )
    op.create_index(op.f('ix_queue_entries_centre_id'), 'queue_entries', ['centre_id'], unique=False)
    op.create_index(op.f('ix_queue_entries_check_in_time'), 'queue_entries', ['check_in_time'], unique=False)
    op.create_index(op.f('ix_queue_entries_is_late'), 'queue_entries', ['is_late'], unique=False)
    op.create_index(op.f('ix_queue_entries_procurement_request_id'), 'queue_entries', ['procurement_request_id'], unique=True)
    op.create_index(op.f('ix_queue_entries_slot_id'), 'queue_entries', ['slot_id'], unique=False)
    op.create_index(op.f('ix_queue_entries_status'), 'queue_entries', ['status'], unique=False)
    op.create_index(op.f('ix_queue_entries_token_id'), 'queue_entries', ['token_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_queue_entries_token_id'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_status'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_slot_id'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_procurement_request_id'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_is_late'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_check_in_time'), table_name='queue_entries')
    op.drop_index(op.f('ix_queue_entries_centre_id'), table_name='queue_entries')
    op.drop_table('queue_entries')

    op.drop_index(op.f('ix_tokens_token_number'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_token_date'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_status'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_slot_id'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_procurement_request_id'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_centre_id'), table_name='tokens')
    op.drop_table('tokens')

    op.drop_index(op.f('ix_token_sequences_token_date'), table_name='token_sequences')
    op.drop_index(op.f('ix_token_sequences_centre_id'), table_name='token_sequences')
    op.drop_table('token_sequences')
