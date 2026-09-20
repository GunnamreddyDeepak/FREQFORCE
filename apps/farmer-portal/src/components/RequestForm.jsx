import { useState } from 'react';
import { DEMO_COMMODITIES, DEMO_FARMER } from '../config/demoData.js';

export default function RequestForm({ onSubmit, isSubmitting }) {
  const todayStr = new Date().toISOString().split('T')[0];

  const [commodityId, setCommodityId] = useState(DEMO_COMMODITIES[0].id);
  const [quantity, setQuantity] = useState('25');
  const [preferredDate, setPreferredDate] = useState(todayStr);

  // Location state
  const [latitude, setLatitude] = useState(DEMO_FARMER.defaultLocation.latitude);
  const [longitude, setLongitude] = useState(DEMO_FARMER.defaultLocation.longitude);
  const [locationMode, setLocationMode] = useState('demo'); // 'demo' | 'live'
  const [geoError, setGeoError] = useState(null);
  const [isLocating, setIsLocating] = useState(false);

  const handleUseLiveLocation = () => {
    setGeoError(null);
    if (!navigator.geolocation) {
      setGeoError('Browser geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(parseFloat(position.coords.latitude.toFixed(4)));
        setLongitude(parseFloat(position.coords.longitude.toFixed(4)));
        setLocationMode('live');
        setIsLocating(false);
      },
      (err) => {
        setIsLocating(false);
        setGeoError(`Location access denied (${err.message}). Using demo farm location.`);
        setLocationMode('demo');
        setLatitude(DEMO_FARMER.defaultLocation.latitude);
        setLongitude(DEMO_FARMER.defaultLocation.longitude);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleUseDemoLocation = () => {
    setGeoError(null);
    setLocationMode('demo');
    setLatitude(DEMO_FARMER.defaultLocation.latitude);
    setLongitude(DEMO_FARMER.defaultLocation.longitude);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const qtyNum = parseFloat(quantity);
    if (isNaN(qtyNum) || qtyNum <= 0) {
      alert('Please enter a valid procurement quantity greater than 0 quintals.');
      return;
    }

    onSubmit({
      farmerId: DEMO_FARMER.id,
      commodityId,
      requestedQuantity: qtyNum,
      preferredDate,
      latitude,
      longitude,
    });
  };

  return (
    <div className="card form-card">
      <div className="card-header">
        <h2 className="card-title">New Procurement Request</h2>
        <p className="card-subtitle">
          Submit your crop details to verify centre eligibility and discover your optimal procurement slot.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="procurement-form">
        {/* 1. Commodity Selection */}
        <div className="form-group">
          <label className="form-label" htmlFor="commodity-select">
            Select Commodity <span className="required">*</span>
          </label>
          <div className="commodity-grid" id="commodity-select" role="radiogroup">
            {DEMO_COMMODITIES.map((c) => {
              const isSelected = commodityId === c.id;
              return (
                <button
                  type="button"
                  key={c.id}
                  className={`commodity-tile ${isSelected ? 'selected' : ''}`}
                  onClick={() => setCommodityId(c.id)}
                  role="radio"
                  aria-checked={isSelected}
                >
                  <span className="commodity-icon">{c.icon}</span>
                  <div className="commodity-tile-text">
                    <span className="commodity-name">{c.name}</span>
                    <span className="commodity-code">{c.code}</span>
                  </div>
                  {isSelected && <span className="tile-check">✓</span>}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Quantity & Date in 2-column layout */}
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label" htmlFor="quantity-input">
              Requested Quantity (Quintals) <span className="required">*</span>
            </label>
            <div className="input-with-unit">
              <input
                id="quantity-input"
                type="number"
                step="0.1"
                min="0.1"
                max="1000"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
                className="form-input"
                placeholder="e.g. 25.0"
              />
              <span className="input-unit">Quintals (qtl)</span>
            </div>
            <span className="field-hint">1 Quintal = 100 Kilograms</span>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="date-input">
              Preferred Date <span className="required">*</span>
            </label>
            <input
              id="date-input"
              type="date"
              min={todayStr}
              value={preferredDate}
              onChange={(e) => setPreferredDate(e.target.value)}
              required
              className="form-input"
            />
            <span className="field-hint">Procurement centres operate daily 09:00 - 17:00</span>
          </div>
        </div>

        {/* 3. Location Selector */}
        <div className="form-group location-group">
          <div className="location-header">
            <label className="form-label" style={{ margin: 0 }}>
              Farmer Farm Location <span className="required">*</span>
            </label>
            <div className="location-toggle-buttons">
              <button
                type="button"
                className={`btn-toggle ${locationMode === 'demo' ? 'active' : ''}`}
                onClick={handleUseDemoLocation}
              >
                📍 Demo Farm
              </button>
              <button
                type="button"
                className={`btn-toggle ${locationMode === 'live' ? 'active' : ''}`}
                onClick={handleUseLiveLocation}
                disabled={isLocating}
              >
                {isLocating ? '📡 Locating...' : '🛰️ Use Live GPS'}
              </button>
            </div>
          </div>

          <div className={`location-status-card ${locationMode === 'live' ? 'live-mode' : 'demo-mode'}`}>
            <div className="location-badge-row">
              <span className={`loc-badge ${locationMode === 'live' ? 'badge-gps' : 'badge-demo-loc'}`}>
                {locationMode === 'live' ? '🛰️ Live GPS Coordinates' : '📍 Seeded Demo Farm Location'}
              </span>
              <span className="coords-text">
                Lat: <strong>{latitude}</strong>, Lng: <strong>{longitude}</strong>
              </span>
            </div>
            <p className="location-note">
              {locationMode === 'live'
                ? 'Using your browser GPS location to calculate accurate road distance to procurement centres.'
                : 'Using default Miryalaguda agricultural belt coordinates for reliable prototype testing.'}
            </p>
          </div>

          {geoError && <p className="field-warning">{geoError}</p>}
        </div>

        {/* 4. Action Button */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-large btn-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Verifying Eligibility...' : 'Check Centre Eligibility & Slots →'}
          </button>
        </div>
      </form>
    </div>
  );
}
