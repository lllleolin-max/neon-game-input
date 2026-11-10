"""Framework-independent gaze input. Optional dependencies are imported lazily."""
from .geometry import Circle, Rect, Surface
from .input import InputFrame, InputMonitor, MouseInput, Sample
from .interaction import Dwell
from .neon import NeonInput

__version__ = "0.1.0"
__all__ = ["Circle", "Rect", "Surface", "InputFrame", "InputMonitor", "MouseInput",
           "Sample", "Dwell", "NeonInput"]
