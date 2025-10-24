import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

interface NavbarProps {
  onLogout: () => void;
}

export default function Navbar({ onLogout }: NavbarProps) {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>Sfera Pulse Dashboard</h1>
      </div>
      <div className="navbar-nav">
        <Link
          to="/pulse"
          className={`nav-link ${location.pathname === '/pulse' ? 'active' : ''}`}
        >
          Pulse
        </Link>
        <Link
          to="/wip"
          className={`nav-link ${location.pathname === '/wip' ? 'active' : ''}`}
        >
          WIP
        </Link>
      </div>
      <div className="navbar-actions">
        <button onClick={onLogout} className="logout-btn">
          Logout
        </button>
      </div>
    </nav>
  );
}
