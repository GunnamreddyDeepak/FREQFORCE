export default function LoadingSpinner({ message = 'Loading...', subtitle }) {
  return (
    <div className="loading-container" role="status" aria-live="polite">
      <div className="spinner-animation">
        <div className="spinner-ring"></div>
        <div className="spinner-core">🌾</div>
      </div>
      <div className="loading-text">
        <p className="loading-message">{message}</p>
        {subtitle && <p className="loading-subtitle">{subtitle}</p>}
      </div>
    </div>
  );
}
