"""Portable entry point: python run_model.py --scenario all."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from pypsa_sudan.model import main
if __name__ == "__main__":
    main()
