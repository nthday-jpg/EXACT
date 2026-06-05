from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from src.physics.router import classify_question


load_dotenv()


HF_API_KEY = os.getenv("HF_API_KEY")
HF_ROUTER_MODEL = "openai/gpt-oss-120b:groq"


def main() -> int:
	if not HF_API_KEY:
		print("SKIP: HF_API_KEY is required for the live router integration test")
		return 0

	classification = classify_question(
		"A charge q1 = +2 μC is at A and q2 = -2 μC is at B, separated by 10 cm. A test charge is placed at the midpoint of AB. Calculate the net force acting on the test charge? If q0 = +1 μC",
		model_name=HF_ROUTER_MODEL,
		api_key=HF_API_KEY,
		temperature=0.0,
	)

	print("Router classification:", classification.domains, classification.question_type)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
