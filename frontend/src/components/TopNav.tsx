import './TopNav.css';

export function TopNav() {
  return (
    <header className="top-nav">
      <div className="brand">
        <span className="brand-title">Network CRM</span>
        <span className="brand-subtitle">Graph + AI</span>
      </div>
      <div className="nav-actions">
        <input className="nav-search" placeholder="Kişi, hedef veya etiket ara" />
        <div className="nav-buttons">
          <button className="ghost-button">Kişi Ekle</button>
          <button className="ghost-button">Goal Ekle</button>
          <button className="primary-button">Vision Ekle</button>
        </div>
        <div className="user-badge">
          <span className="avatar">FB</span>
          <div className="user-meta">
            <strong>Fahri Bilgen</strong>
            <small>admin@networkcrm</small>
          </div>
        </div>
      </div>
    </header>
  );
}
