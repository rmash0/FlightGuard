import { NavLink, Outlet } from "react-router";

import { APP_NAME } from "../config";
import BubbleBackground from "./aero/BubbleBackground";
import GlassPanel from "./aero/GlassPanel";
import ThemeToggle from "./aero/ThemeToggle";
import "./Layout.css";

function Layout() {
  return (
    <div className="app-shell">
      <BubbleBackground />

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
