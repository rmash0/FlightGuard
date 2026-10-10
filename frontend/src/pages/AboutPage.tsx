import { APP_NAME } from "../config";

function AboutPage() {
  return (
    <section>
      <h1>About {APP_NAME}</h1>
      <p>
        {APP_NAME} predicts delays for US airline flights and shows each
        flight's estimated carbon footprint.
      </p>
      <p>
        Data: AeroDataBox, Open-Meteo, FAA NAS Status, Bureau of
        Transportation Statistics, Google Travel Impact Model, OpenSky
        Network.
      </p>
    </section>
  );
}

export default AboutPage;
