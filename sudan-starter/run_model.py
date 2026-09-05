"""Default: full 2022 reference year. Legacy 2024 cases require explicit selection."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import argparse
from pypsa_sudan.model import read_inputs, run
from pypsa_sudan.reference import run_reference

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="reference_2022", choices=["reference_2022", "all"] + list(read_inputs()[1]))
    parser.add_argument("--hours", type=int, help="Legacy 2024 cases only; 2022 always uses the full year")
    args = parser.parse_args()
    if args.scenario == "reference_2022":
        if args.hours is not None:
            parser.error("reference_2022 uses all 8760 hours; --hours applies only to legacy scenarios")
        run_reference()
    else:
        run(None if args.scenario == "all" else [args.scenario], hours=args.hours)

if __name__ == "__main__":
    main()
