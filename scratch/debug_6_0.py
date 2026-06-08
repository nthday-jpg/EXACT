import sys
from pathlib import Path
import re

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas
from src.logic.reasoning.solver import verify_conclusion

premises = [
  "ForAll(x, (VehicleInspection(x) AND AppropriateLicense(x) -> TransportStandardGoods(x)))",
  "ForAll(x, (TransportStandardGoods(x) AND HazmatTraining(x) AND SafetyEndorsement(x) -> TransportHazardousMaterials(x)))",
  "ForAll(x, (TransportHazardousMaterials(x) AND InterstatePermit(x) -> CrossStateLinesWithHazardousCargo(x)))",
  "VehicleInspection(john)",
  "AppropriateLicense(john)",
  "HazmatTraining(john)",
  "NOT SafetyEndorsement(john)",
  "InterstatePermit(john)"
]

options_texts = [
    "John can transport hazardous materials but cannot cross state lines",
    "John can cross state lines with hazardous cargo",
    "John cannot transport hazardous materials",
    "John is not qualified to transport any kind of goods"
]

# We need to simulate how the model translates the options.
# Wait! In the actual run, the options are translated by the LLM.
# Let's check what the LLM translated the options to in the evaluation!
# Wait, does the failed case log the translated options?
# Let's search data/fol_failed_cases.json for "example_id": "6_0" or look at the logs.
# Let's read lines 80 to 180 of fol_failed_cases.json to see if there is any other info.
