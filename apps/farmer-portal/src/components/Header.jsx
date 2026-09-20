export default function Header() {
  return (
    <header className="app-header">
      <div className="header-container">
        <div className="brand-group">
          <div className="emblem-container">
            <span className="emblem-icon" role="img" aria-label="KisanQueue Emblem">🌾</span>
          </div>
          <div className="brand-titles">
            <div className="brand-main">
              <span className="brand-name">KISANQUEUE</span>
              <span className="portal-tag">FARMER PORTAL</span>
            </div>
            <p className="brand-subtitle">
              KISANQUEUE Prototype • Intelligent Procurement Platform (SIH 2026)
            </p>
          </div>
        </div>

        <div className="header-meta">
          <div className="status-indicator">
            <span className="pulse-dot"></span>
            <span className="status-label">Live Procurement Operational</span>
          </div>
        </div>
      </div>
    </header>
  );
}
