import { NavLink, Outlet, useMatch } from "react-router";

import { APP_NAME } from "../config";
import GlassPanel from "./aero/GlassPanel";
import MusicToggle from "./aero/MusicToggle";
import SkyBackground from "./aero/SkyBackground";
import ThemeToggle from "./aero/ThemeToggle";
import "./Layout.css";

function Layout() {
  // Results pages are part of the search flow, so keep the Search tab lit there too.
  const onResultsPage = useMatch("/flight/*") !== null;

  return (
    <div className="app-shell">
      <SkyBackground />

      <GlassPanel as="header" className="app-header">
        <NavLink to="/" className="app-brand">
          <img src="/favicon.svg" alt="" width="32" height="32" />
          {APP_NAME}
        </NavLink>

        <nav className="app-nav" aria-label="Main">
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive || onResultsPage ? "active" : undefined)}
          >
            Search
          </NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/about">About</NavLink>
        </nav>
        <div className="app-header__toggles">
          <MusicToggle />
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
