export default function ErrorBanner({ message, onRetry, onDismiss }) {
  if (!message) return null;

  return (
    <div className="error-banner" role="alert">
      <div className="error-icon">⚠️</div>
      <div className="error-content">
        <h4 className="error-title">Action Failed</h4>
        <p className="error-message">{message}</p>
      </div>
      <div className="error-actions">
        {onRetry && (
          <button type="button" className="btn-retry" onClick={onRetry}>
            Try Again
          </button>
        )}
        {onDismiss && (
          <button type="button" className="btn-dismiss" onClick={onDismiss} aria-label="Dismiss error">
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
