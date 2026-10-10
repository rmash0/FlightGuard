import type { Emissions } from "../../types/api";

type EmissionsCardProps = {
  emissions: Emissions | null;
};

// Placeholder owned by Role D: keep these props, replace the insides.
function EmissionsCard({ emissions }: EmissionsCardProps) {
  if (!emissions) {
    return <p>CO2 estimate unavailable for this flight.</p>;
  }

  return (
    <p>
      About {Math.round(emissions.co2e_kg_per_passenger.economy)} kg CO2e per
      economy passenger
    </p>
  );
}

export default EmissionsCard;
