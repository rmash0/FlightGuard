
GRAMS_PER_KG = 1000
EARTH_RADIUS_KM = 6371

CO2_KG_PER_PASSENGER_KM = 0.09

CAR_CO2_KG_PER_KM = 0.251

TREE_CO2_KG_PER_YEAR = 60.5

PERSON_CO2_KG_PER_YEAR = 16000
PERSON_CO2_KG_PER_DAY = PERSON_CO2_KG_PER_YEAR / 365

# EPA equivalencies (Oct 2024 update, iPhone 16 data): 1.24e-5 metric tons CO2 per charge
SMARTPHONE_CHARGE_CO2_KG = 0.0124

CABIN_MULTIPLIERS = {
    "economy": 1.0,
    "premium_economy": 1.5,
    "business": 2.0,
    "first": 3.0,
}

CONSTANT_SOURCES = {
    "car": (
        "https://www.epa.gov/greenvehicles/"
        "greenhouse-gas-emissions-typical-passenger-vehicle"
    ),
    "tree": (
        "https://www.epa.gov/energy/"
        "greenhouse-gas-equivalencies-calculator-calculations-and-references"
    ),
    "person": "Illustrative assumption of 16 metric tons CO2e per year",
    "smartphone": (
        "https://www.epa.gov/energy/"
        "greenhouse-gas-equivalencies-calculator-calculations-and-references"
    ),
    "flight": "Approximate distance-based fallback assumption",
}
