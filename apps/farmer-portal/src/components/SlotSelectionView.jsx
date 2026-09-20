import { useState } from 'react';

function formatTimeWindow(startTime, endTime) {
  if (!startTime || !endTime) return 'Standard Window';
  const formatTime = (t) => {
    const [h, m] = t.split(':');
    const hour = parseInt(h, 10);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const formattedHour = hour % 12 === 0 ? 12 : hour % 12;
    return `${formattedHour}:${m} ${ampm}`;
  };
  return `${formatTime(startTime)} – ${formatTime(endTime)}`;
}

export default function SlotSelectionView({
  centre,
  slotsData,
  date,
  requestedQuantity,
  onConfirmBooking,
  onBackToRecommendation,
  isConfirming,
}) {
  const slots = slotsData?.slots || [];
  const [selectedSlotId, setSelectedSlotId] = useState(
    slots.find((s) => s.status === 'OPEN' && (s.remaining_quantity >= requestedQuantity || s.available_quantity >= requestedQuantity))?.slot_id ||
    slots[0]?.slot_id ||
    null
  );

  const selectedSlot = slots.find((s) => s.slot_id === selectedSlotId);

  const handleConfirm = () => {
    if (selectedSlotId) {
      onConfirmBooking(centre.centre_id, selectedSlotId);
    }
  };

  return (
    <div className="card slot-card">
      <div className="card-header">
        <div className="title-with-badge">
          <h2 className="card-title">Select Arrival Slot Window</h2>
          <span className="badge badge-primary">{date}</span>
        </div>
        <p className="card-subtitle">
          Procurement Centre: <strong>{centre.centre_name}</strong> ({centre.centre_code})
        </p>
      </div>

      <div className="slot-selection-body">
        <div className="centre-summary-strip">
          <div className="summary-item">
            <span className="summary-label">Target Date</span>
            <span className="summary-val">{date}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Requested Quantity</span>
            <span className="summary-val">{requestedQuantity} Quintals</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Daily Capacity</span>
            <span className="summary-val">{slotsData?.daily_capacity_qtl ?? centre.available_capacity} qtl</span>
          </div>
        </div>

        {slots.length === 0 ? (
          <div className="empty-state-box">
            <span className="empty-state-icon">⏳</span>
            <h3>No Scheduled Slots Available</h3>
            <p>No operational slots are currently generated for this centre on {date}.</p>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onBackToRecommendation}
            >
              ← Choose Another Centre
            </button>
          </div>
        ) : (
          <div className="slots-grid">
            {slots.map((slot) => {
              const isOpen = slot.status === 'OPEN';
              const availableQty = slot.remaining_quantity !== undefined ? slot.remaining_quantity : (slot.available_quantity !== undefined ? slot.available_quantity : (slot.quantity_capacity - slot.booked_quantity));
              const remainingBookings = slot.remaining_bookings !== undefined ? slot.remaining_bookings : (slot.available_bookings !== undefined ? slot.available_bookings : (slot.max_bookings - slot.booked_bookings));
              const hasCapacity = availableQty >= requestedQuantity && remainingBookings > 0;
              const isAvailable = isOpen && hasCapacity;
              const isSelected = selectedSlotId === slot.slot_id;

              return (
                <div
                  key={slot.slot_id}
                  className={`slot-tile ${isSelected ? 'selected' : ''} ${!isAvailable ? 'disabled' : ''}`}
                  onClick={() => isAvailable && setSelectedSlotId(slot.slot_id)}
                >
                  <div className="slot-tile-header">
                    <span className="slot-time-badge">
                      ⏰ {formatTimeWindow(slot.start_time, slot.end_time)}
                    </span>
                    <span className={`slot-status-tag ${isOpen ? 'status-open' : 'status-closed'}`}>
                      {slot.status}
                    </span>
                  </div>

                  <div className="slot-tile-body">
                    <div className="slot-metric-row">
                      <span className="slot-metric-label">Slot Capacity:</span>
                      <span className="slot-metric-val">
                        <strong>{availableQty}</strong> / {slot.quantity_capacity} qtl
                      </span>
                    </div>

                    <div className="slot-metric-row">
                      <span className="slot-metric-label">Vehicle Bookings:</span>
                      <span className="slot-metric-val">
                        <strong>{remainingBookings}</strong> / {slot.max_bookings} available
                      </span>
                    </div>

                    {!hasCapacity && isOpen && (
                      <p className="slot-warning-text">Insufficient remaining quantity for {requestedQuantity} qtl</p>
                    )}
                  </div>

                  <div className="slot-radio-indicator">
                    <input
                      type="radio"
                      name="slot_choice"
                      checked={isSelected}
                      disabled={!isAvailable}
                      onChange={() => isAvailable && setSelectedSlotId(slot.slot_id)}
                      id={`slot-radio-${slot.slot_id}`}
                    />
                    <label htmlFor={`slot-radio-${slot.slot_id}`}>
                      {isSelected ? 'Selected Slot' : isAvailable ? 'Select This Window' : 'Unavailable'}
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Action Controls */}
        <div className="card-actions-row">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onBackToRecommendation}
            disabled={isConfirming}
          >
            ← Change Centre
          </button>
          <button
            type="button"
            className="btn btn-primary btn-large"
            onClick={handleConfirm}
            disabled={!selectedSlot || isConfirming}
          >
            {isConfirming ? 'Securing Slot & Issuing Token...' : 'Confirm Slot & Generate Token →'}
          </button>
        </div>
      </div>
    </div>
  );
}
