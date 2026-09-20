const REASON_LABELS = {
  COMMODITY_SUPPORTED: 'Commodity Supported',
  CENTRE_ACTIVE: 'Centre Active',
  CAPACITY_AVAILABLE: 'Capacity Available',
  UNSUPPORTED_COMMODITY: 'Commodity Not Handled',
  INSUFFICIENT_CAPACITY: 'Capacity Exhausted',
  INACTIVE_CENTRE: 'Centre Inactive',
  NO_CAPACITY_RECORD: 'No Daily Capacity Scheduled',
};

export default function EligibilityView({
  eligibilityData,
  requestDetails,
  onProceedToRecommendation,
  onModifyRequest,
  isLoading,
}) {
  const eligibleCentres = eligibilityData?.eligible_centres || [];
  const hasEligibleCentres = eligibleCentres.length > 0;

  return (
    <div className="card eligibility-card">
      <div className="card-header">
        <div className="title-with-badge">
          <h2 className="card-title">Centre Eligibility Evaluation</h2>
          <span className={`badge ${hasEligibleCentres ? 'badge-success' : 'badge-danger'}`}>
            {hasEligibleCentres
              ? `${eligibleCentres.length} Eligible Centres Found`
              : 'No Eligible Centres'}
          </span>
        </div>
        <p className="card-subtitle">
          Backend verified commodity capability and daily capacity for{' '}
          <strong>{requestDetails.requestedQuantity} quintals</strong> on{' '}
          <strong>{requestDetails.preferredDate}</strong>.
        </p>
      </div>

      {!hasEligibleCentres ? (
        <div className="empty-state-box">
          <span className="empty-state-icon">🚫</span>
          <h3>No Procurement Centres Found For This Request</h3>
          <p>
            None of the active procurement centres can accommodate{' '}
            <strong>{requestDetails.requestedQuantity} qtl</strong> on{' '}
            <strong>{requestDetails.preferredDate}</strong>.
          </p>
          <div className="empty-state-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onModifyRequest}
            >
              ← Modify Request Details
            </button>
          </div>
        </div>
      ) : (
        <div className="eligibility-content">
          <div className="centres-list">
            {eligibleCentres.map((centre) => (
              <div key={centre.centre_id} className="centre-item-card">
                <div className="centre-header-row">
                  <div>
                    <h3 className="centre-title">{centre.centre_name}</h3>
                    <span className="centre-code-tag">{centre.centre_code}</span>
                  </div>
                  <div className="capacity-badge">
                    <span className="capacity-value">{centre.available_capacity}</span>
                    <span className="capacity-unit">qtl available today</span>
                  </div>
                </div>

                <div className="centre-reasons">
                  <span className="reasons-label">Verification:</span>
                  <div className="reason-tags">
                    {centre.reasons && centre.reasons.length > 0 ? (
                      centre.reasons.map((r, i) => (
                        <span key={i} className="reason-pill">
                          ✓ {REASON_LABELS[r] || r}
                        </span>
                      ))
                    ) : (
                      <span className="reason-pill">✓ Verified</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="card-actions-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onModifyRequest}
              disabled={isLoading}
            >
              ← Edit Request
            </button>
            <button
              type="button"
              className="btn btn-primary btn-large"
              onClick={onProceedToRecommendation}
              disabled={isLoading}
            >
              {isLoading ? 'Computing Recommendation...' : 'Get Optimal Centre Recommendation →'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
