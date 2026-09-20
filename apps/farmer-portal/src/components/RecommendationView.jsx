import { useState } from 'react';

const REASON_DESCRIPTIONS = {
  CENTRE_ACTIVE: 'Operational Facility',
  COMMODITY_SUPPORTED: 'Commodity Capability Match',
  CAPACITY_AVAILABLE: 'Capacity Available',
  LOWER_CAPACITY_PRESSURE: 'Lower Capacity Pressure',
  AVAILABLE_CAPACITY_REMAINING: 'Available Capacity Remaining',
  NEAREST_ELIGIBLE_CENTRE: 'Nearest Eligible Centre',
};

export default function RecommendationView({
  recommendationData,
  onSelectCentreAndProceed,
  onBack,
  isLoading,
}) {
  const recommended = recommendationData?.recommended_centre;
  const alternatives = recommendationData?.alternative_centres || [];

  // Default selection to recommended centre
  const [selectedCentreId, setSelectedCentreId] = useState(
    recommended ? recommended.centre_id : (alternatives[0]?.centre_id || null)
  );

  const selectedCentre =
    recommended && recommended.centre_id === selectedCentreId
      ? recommended
      : alternatives.find((alt) => alt.centre_id === selectedCentreId) || recommended;

  const handleProceed = () => {
    if (selectedCentre) {
      onSelectCentreAndProceed(selectedCentre);
    }
  };

  return (
    <div className="card recommendation-card">
      <div className="card-header">
        <h2 className="card-title">Recommended Procurement Centre</h2>
        <p className="card-subtitle">
          Backend optimization evaluated spatial distance, facility utilization, and available capacity.
        </p>
      </div>

      <div className="recommendation-content">
        {/* 1. Recommended Centre Card (Primary) */}
        {recommended && (
          <div
            className={`rec-hero-card ${selectedCentreId === recommended.centre_id ? 'is-selected' : ''}`}
            onClick={() => setSelectedCentreId(recommended.centre_id)}
          >
            <div className="rec-ribbon">
              ⭐ Top Recommended
            </div>

            <div className="rec-hero-main">
              <div className="rec-title-group">
                <h3 className="rec-centre-name">{recommended.centre_name}</h3>
                <span className="rec-centre-code">{recommended.centre_code}</span>
              </div>

              <div className="rec-metrics-grid">
                <div className="metric-box">
                  <span className="metric-icon">🚗</span>
                  <div className="metric-data">
                    <span className="metric-value">{recommended.distance_km.toFixed(1)} km</span>
                    <span className="metric-label">Distance from farm</span>
                  </div>
                </div>

                <div className="metric-box">
                  <span className="metric-icon">📦</span>
                  <div className="metric-data">
                    <span className="metric-value">{recommended.available_capacity} qtl</span>
                    <span className="metric-label">Remaining capacity</span>
                  </div>
                </div>

                <div className="metric-box">
                  <span className="metric-icon">📊</span>
                  <div className="metric-data">
                    <span className="metric-value">{(recommended.score * 100).toFixed(1)}%</span>
                    <span className="metric-label">Optimization Score</span>
                  </div>
                </div>
              </div>

              <div className="rec-reasons-container">
                <span className="reasons-heading">Recommendation Factors:</span>
                <div className="reason-chips">
                  {recommended.reasons?.map((r, i) => (
                    <span key={i} className="chip chip-success">
                      ✓ {REASON_DESCRIPTIONS[r] || r}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rec-selection-indicator">
                <input
                  type="radio"
                  name="selected_centre"
                  checked={selectedCentreId === recommended.centre_id}
                  onChange={() => setSelectedCentreId(recommended.centre_id)}
                  id={`radio-${recommended.centre_id}`}
                />
                <label htmlFor={`radio-${recommended.centre_id}`}>
                  {selectedCentreId === recommended.centre_id
                    ? 'Selected for Slot Booking'
                    : 'Click to select this centre'}
                </label>
              </div>
            </div>
          </div>
        )}

        {/* 2. Alternative Centres Section */}
        {alternatives.length > 0 && (
          <div className="alternatives-section">
            <h4 className="section-subtitle">Alternative Eligible Centres</h4>
            <div className="alternatives-list">
              {alternatives.map((alt) => {
                const isSelected = selectedCentreId === alt.centre_id;
                return (
                  <div
                    key={alt.centre_id}
                    className={`alt-card ${isSelected ? 'is-selected' : ''}`}
                    onClick={() => setSelectedCentreId(alt.centre_id)}
                  >
                    <div className="alt-header">
                      <div>
                        <h4 className="alt-name">{alt.centre_name}</h4>
                        <span className="alt-code">{alt.centre_code}</span>
                      </div>
                      <input
                        type="radio"
                        name="selected_centre"
                        checked={isSelected}
                        onChange={() => setSelectedCentreId(alt.centre_id)}
                      />
                    </div>

                    <div className="alt-metrics">
                      <span className="alt-metric-tag">
                        🚗 {alt.distance_km.toFixed(1)} km
                      </span>
                      <span className="alt-metric-tag">
                        📦 {alt.available_capacity} qtl
                      </span>
                      <span className="alt-metric-tag">
                        📊 {(alt.score * 100).toFixed(1)}% score
                      </span>
                    </div>

                    <div className="alt-reasons">
                      {alt.reasons?.map((r, i) => (
                        <span key={i} className="chip chip-neutral">
                          {REASON_DESCRIPTIONS[r] || r}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div className="card-actions-row">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onBack}
            disabled={isLoading}
          >
            ← Back to Eligibility
          </button>
          <button
            type="button"
            className="btn btn-primary btn-large"
            onClick={handleProceed}
            disabled={!selectedCentre || isLoading}
          >
            {isLoading ? 'Loading Slots...' : `Select Slots at ${selectedCentre?.centre_name?.split(' ')[0] || 'Centre'} →`}
          </button>
        </div>
      </div>
    </div>
  );
}
