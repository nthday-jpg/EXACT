import sys
import os


try:
    from src.physics.preprocessing import preprocess
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please run this script from the project root directory or ensure 'src' is in your PYTHONPATH.")
    sys.exit(1)


def run_tests():
    test_cases = [
        # Basic conversions
        ("10 m", "10 m"),
        ("10 mm", "0.01 m"),
        ("10 cm^2", "0.001 m^2"),
        
        # Single-unit conversions
        ("5 kOhm", "5000 ohm"),
        ("10 uF", "1e-05 F"),
        ("120 MHz", "1.2e8 Hz"),
        
        # Mass unit conversion (g to kg)
        ("1 kg", "1 kg"),
        ("1 g", "0.001 kg"),
        ("1 mg", "1e-06 kg"),
        
        # Composite units (multiplication & division)
        ("rho = 0.5 ohm*mm^2/m", "rho = 5e-07 ohm*m^2/m"),
        ("density = 1 g/cm^3", "density = 1000 kg/m^3"),
        ("velocity = 72 km/h", "velocity = 72000 m/h"),  # 'h' remains unchanged, 'km' scales to 'm'
        
        # Sentence structures with multiple units
        (
            "The resistor is 5 kOhm and the density of water is 1 g/cm^3.",
            "The resistor is 5000 ohm and the density of water is 1000 kg/m^3."
        )
    ]

    all_passed = True
    for i, (input_text, expected_output) in enumerate(test_cases, start=1):
        result = preprocess(input_text)
        try:
            assert result == expected_output, f"Expected '{expected_output}', but got '{result}'"
            print(f"Test case {i} PASSED")
        except AssertionError as err:
            print(f"Test case {i} FAILED: {err}")
            all_passed = False

    if all_passed:
        print("\nAll integration test cases passed successfully.")
        sys.exit(0)
    else:
        print("\nSome integration test cases failed.")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()