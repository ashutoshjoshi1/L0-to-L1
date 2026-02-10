from dataclasses import dataclass, field
from typing import Optional, Dict
import numpy as np


@dataclass
class L0Record:
    timestamp: str
    integration_time_ms: float
    spectrum_counts: np.ndarray
    dark_counts: Optional[np.ndarray] = None
    temperature_c: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class L1Record:
    timestamp: str
    integration_time_ms: float
    spectrum: np.ndarray            # corrected spectrum (counts or count-rate depending on s-code)
    uncertainty: np.ndarray         # matching unit uncertainty
    processing_flag: int
    dqf: int
    metadata: Dict = field(default_factory=dict)
