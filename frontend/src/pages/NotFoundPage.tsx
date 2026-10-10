import { Link } from "react-router";

import GlassPanel from "../components/aero/GlassPanel";
import { aeroButtonClass } from "../components/aero/classes";

function NotFoundPage() {
  return (
    <GlassPanel as="section">
      <h1>This page flew off course</h1>
      <p className="text-muted">We couldn't find what you were looking for.</p>
      <Link to="/" className={aeroButtonClass()}>
        Back to search
      </Link>
    </GlassPanel>
  );
}

export default NotFoundPage;
