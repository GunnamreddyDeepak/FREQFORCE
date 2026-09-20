export default function FarmerProfileBadge({ farmer }) {
  if (!farmer) return null;

  return (
    <aside className="farmer-profile-card" aria-label="Farmer Profile Info">
      <div className="farmer-avatar">
        <span className="avatar-icon">🧑‍🌾</span>
      </div>
      <div className="farmer-details">
        <div className="farmer-name-row">
          <span className="farmer-name">{farmer.fullName}</span>
          <span className="badge-demo">Demo Profile</span>
        </div>
        <div className="farmer-meta-row">
          <span className="meta-item">📍 {farmer.village}, {farmer.district}, {farmer.state}</span>
          <span className="meta-item">📞 +91 {farmer.phoneNumber}</span>
        </div>
      </div>
    </aside>
  );
}
