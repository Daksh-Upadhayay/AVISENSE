import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, History, Settings, Plane } from 'lucide-react';
import styles from './Layout.module.css';

const Layout = ({ children }) => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className="container flex items-center justify-between">
          <div className={styles.logo}>
            <Plane className={styles.logoIcon} />
            <span className={styles.logoText}>Avisense</span>
          </div>
          <nav className={styles.nav}>
            <Link to="/" className={`${styles.navLink} ${isActive('/') ? styles.active : ''}`}>
              <Activity size={18} />
              <span>Quick Check</span>
            </Link>
            <Link to="/history" className={`${styles.navLink} ${isActive('/history') ? styles.active : ''}`}>
              <History size={18} />
              <span>History</span>
            </Link>
            <Link to="/settings" className={`${styles.navLink} ${isActive('/settings') ? styles.active : ''}`}>
              <Settings size={18} />
              <span>Settings</span>
            </Link>
          </nav>
        </div>
      </header>
      <main className={styles.main}>
        <div className="container">
          {children}
        </div>
      </main>
      <footer className={styles.footer}>
        <div className="container text-center">
          <p>&copy; 2025 Avisense Engine Safety Systems. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
