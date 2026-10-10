import { NavLink, Outlet } from "react-router";

import { APP_NAME } from "../config";
import GlassPanel from "./aero/GlassPanel";
import SkyBackground from "./aero/SkyBackground";
import ThemeToggle from "./aero/ThemeToggle";
import "./Layout.css";

function Layout() {
  return (
    <div className="app-shell">
      <SkyBackground />

      <GlassPanel as="header" className="app-header">
        <NavLink to="/" className="app-brand">
          <img src="/favicon.svg" alt="" width="32" height="32" />
          {APP_NAME}
        </NavLink>

        <div className="app-header__actions">
          <nav className="app-nav" aria-label="Main">
            <NavLink to="/" end>
              Search
            </NavLink>
            <NavLink to="/map">Map</NavLink>
            <NavLink to="/about">About</NavLink>
          </nav>
          <ThemeToggle />
        </div>
      </GlassPanel>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
