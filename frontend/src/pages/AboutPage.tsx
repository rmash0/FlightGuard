import { useEffect } from "react";
import { useLocation } from "react-router";

import GlassPanel from "../components/aero/GlassPanel";
import FeatureList from "../components/features/FeatureList";
import { APP_NAME } from "../config";

function AboutPage() {
  const { hash } = useLocation();
  const targetId = hash.slice(1);

  // Client-side navigation doesn't scroll to #anchors on its own.
  useEffect(() => {
    if (targetId) {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [targetId]);

  return (
    <>
      <GlassPanel as="section">
        <h1>About {APP_NAME}</h1>
        <p>
          {APP_NAME} predicts delays for US airline flights and shows each
          flight's estimated carbon footprint.
        </p>
      </GlassPanel>

      <FeatureList variant="cards" highlightedId={targetId} />

      <GlassPanel as="section" className="about-credits">
        <p className="text-muted">
          Data: AeroDataBox, Open-Meteo, FAA NAS Status, Bureau of
          Transportation Statistics, Google Travel Impact Model, OpenSky
          Network.
        </p>
      </GlassPanel>
    </>
  );
}

export default AboutPage;
