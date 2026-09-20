export default function ConfirmationView({
  bookingResult,
  farmer,
  commodity,
  onBookAnother,
}) {
  const token = bookingResult?.token;
  const tokenNumber = token?.token_number || 'PENDING';

  return (
    <div className="card confirmation-card">
      <div className="confirmation-header-banner">
        <div className="success-icon-badge">✓</div>
        <h2 className="confirmation-title">Procurement Slot Confirmed!</h2>
        <p className="confirmation-lead">
          Your arrival token has been issued by the KISANQUEUE allocation engine.
        </p>
      </div>

      {/* Digital Token Pass Ticket */}
      <div className="token-pass-container">
        <div className="token-pass-header">
          <div className="pass-emblem">🌾</div>
          <div className="pass-title-box">
            <span className="pass-org">KISANQUEUE DIGITAL PROCUREMENT PASS</span>
            <span className="pass-dept">KISANQUEUE Prototype • Smart Agri Logistics (SIH 2026)</span>
          </div>
          <div className="pass-status-pill">
            {bookingResult.status || 'SLOT_CONFIRMED'}
          </div>
        </div>

        {/* Large Prominent Token Display */}
        <div className="token-hero-box">
          <span className="token-label">ARRIVAL TOKEN NUMBER</span>
          <h1 className="token-number-display">{tokenNumber}</h1>
          <span className="token-sub">
            Present this token number at the procurement yard gate check-in desk
          </span>
        </div>

        {/* Details Grid */}
        <div className="pass-grid">
          <div className="pass-grid-item">
            <span className="grid-label">Procurement Centre</span>
            <span className="grid-val font-semibold">{bookingResult.centre_name}</span>
          </div>

          <div className="pass-grid-item">
            <span className="grid-label">Reporting Date</span>
            <span className="grid-val font-semibold">{bookingResult.slot_date}</span>
          </div>

          <div className="pass-grid-item">
            <span className="grid-label">Slot Time Window</span>
            <span className="grid-val highlight-green">{bookingResult.slot_window}</span>
          </div>

          <div className="pass-grid-item">
            <span className="grid-label">Booked Quantity</span>
            <span className="grid-val font-semibold">
              {bookingResult.booked_quantity} Quintals ({commodity?.name || 'Produce'})
            </span>
          </div>

          <div className="pass-grid-item">
            <span className="grid-label">Farmer Name</span>
            <span className="grid-val">{farmer?.fullName}</span>
          </div>

          <div className="pass-grid-item">
            <span className="grid-label">Farmer Contact</span>
            <span className="grid-val">+91 {farmer?.phoneNumber}</span>
          </div>

          <div className="pass-grid-item full-width">
            <span className="grid-label">Procurement Request ID</span>
            <span className="grid-val font-mono">{bookingResult.procurement_request_id}</span>
          </div>
        </div>

        {/* Important Farmer Instructions */}
        <div className="pass-instructions">
          <h4 className="instructions-title">📋 Important Farmer Instructions:</h4>
          <ul className="instructions-list">
            <li>Please arrive at the procurement centre during your assigned time window (<strong>{bookingResult.slot_window}</strong>).</li>
            <li>Carry valid Farmer Photo ID and vehicle registration details.</li>
            <li>Ensure grain moisture complies with standardized Fair Average Quality (FAQ) norms.</li>
            <li>Show this token number (<strong>{tokenNumber}</strong>) at the security gate for immediate entry into the processing queue.</li>
          </ul>
        </div>
      </div>

      {/* Confirmation Actions */}
      <div className="confirmation-actions">
        <button
          type="button"
          className="btn btn-outline"
          onClick={() => window.print()}
        >
          🖨️ Print Booking Pass
        </button>
        <button
          type="button"
          className="btn btn-primary btn-large"
          onClick={onBookAnother}
        >
          Book Another Request →
        </button>
      </div>
    </div>
  );
}
