import { Link, useLocation, useSearchParams } from 'react-router-dom';
import './Navbar.css';

interface NavbarProps {
  onLogout: () => void;
}

export default function Navbar({ onLogout }: NavbarProps) {
  const location = useLocation();
  const [searchParams] = useSearchParams();

  // Create links that preserve current URL parameters
  const createLinkWithParams = (path: string) => {
    const currentParams = searchParams.toString();
    return currentParams ? `${path}?${currentParams}` : path;
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>Sfera Pulse Dashboard</h1>
      </div>
      <div className="navbar-nav">
        <Link
          to={createLinkWithParams("/pulse")}
          className={`nav-link ${location.pathname === '/pulse' ? 'active' : ''}`}
        >
          Pulse
        </Link>
        <Link
          to={createLinkWithParams("/wip")}
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
