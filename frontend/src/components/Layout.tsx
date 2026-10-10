import { NavLink, Outlet } from "react-router";

import { APP_NAME } from "../config";

function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink to="/" className="app-brand">
          {APP_NAME}
        </NavLink>
        <nav className="app-nav" aria-label="Main">
          <NavLink to="/" end>
            Search
          </NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/about">About</NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
