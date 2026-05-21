"""Design council — fuses 5 specialist agents into a Hallmark-compatible brief."""
from tools.council.orchestrator import run_council
from tools.council._models import CouncilResult

__all__ = ["run_council", "CouncilResult"]
