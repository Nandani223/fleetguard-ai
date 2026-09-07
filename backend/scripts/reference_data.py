"""
Reference data + tunable constants for the FleetGuard synthetic data
generator. Kept separate from generate_data.py so the "knobs" are easy
to find and adjust without wading through generation logic.
"""
from datetime import date

SEED = 42

# --- Scale (per brief: 300-500 vehicles, 3-5 parts, 150-250 failures) ---
N_VEHICLES = 400
SIM_START = date(2025, 1, 1)   # 12 months of weekly telematics from here
SIM_WEEKS = 52

# --- Parts master ---
# design_life_km is the manufacturer-rated life used by the RUL estimator later.
PARTS = [
    {"part_code": "ELC-0152", "part_name": "Alternator",          "category": "Electrical", "design_life_km": 150_000},
    {"part_code": "COL-0210", "part_name": "Radiator",            "category": "Cooling",     "design_life_km": 220_000},
    {"part_code": "CHS-0330", "part_name": "Brake Pads",          "category": "Chassis",     "design_life_km": 100_000},
    {"part_code": "CHS-0410", "part_name": "Suspension Bushings", "category": "Chassis",     "design_life_km": 180_000},
    {"part_code": "ENG-0500", "part_name": "Turbocharger",        "category": "Engine",      "design_life_km": 260_000},
]

# --- Wear-based failure model constants (non-alternator parts) ---
# raw_wear = clip(total_km_driven / design_life_km, 0, WEAR_RAW_CAP)   <- capped BEFORE roughness
# wear = raw_wear * region_roughness   (Chassis/Engine only; Cooling/Radiator unaffected -> control part)
# p = clip(WEAR_K[code] * wear ** WEAR_EXPONENT, 0, 0.6)
# Capping the raw km-based ratio *before* applying roughness (rather than after)
# matters: if you cap after, short-life parts saturate the cap regardless of
# region and the confounder effect disappears in the failure counts even
# though it's still visible in the telematics. Capping raw first leaves room
# for roughness to actually move the needle on failure probability.
WEAR_K = {
    "COL-0210": 0.10,
    "CHS-0330": 0.09,
    "CHS-0410": 0.09,
    "ENG-0500": 0.075,
}
WEAR_RAW_CAP = 1.3
WEAR_EXPONENT = 1.3

# --- Alternator failure model (primary signal relationship) ---
ALTERNATOR_INTERCEPT = -6.6
ALTERNATOR_DEGRADATION_COEF = 4.1

# --- Vehicle attribute pools ---
MODELS = ["Long-Haul Tractor", "Regional Box Truck", "City Delivery Van", "Heavy Tipper"]
REGIONS = ["North", "South", "East", "West"]

# Region confounder: North has rougher roads -> elevated harsh braking + overload
# duty share, which accelerates wear on brakes, suspension, AND turbo (engine strain),
# not just one part. This is what makes it a genuine confounder rather than a
# single hard-coded correlation.
REGION_ROAD_ROUGHNESS = {
    "North": 1.35,
    "East": 1.05,
    "South": 0.90,
    "West": 0.85,
}

# Usage intensity multiplier per vehicle (drawn from a distribution per vehicle,
# not fixed) -> some vehicles do ~3x the monthly km of others, like a real fleet.
USAGE_INTENSITY_MEAN = 1.0
USAGE_INTENSITY_STD = 0.45
USAGE_INTENSITY_MIN = 0.35
USAGE_INTENSITY_MAX = 3.0
BASE_MONTHLY_KM = 4200  # at usage_intensity == 1.0

VIN_ALPHABET = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"  # excludes I, O, Q like real VINs
FLEET_OWNERS = ['Continental Freight Co.', 'Summit Logistics Group', 'Harborline Transport']
