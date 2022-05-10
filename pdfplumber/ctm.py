import math
from typing import NamedTuple

# For more details, see the PDF Reference, 6th Ed., Section 4.2.2 ("Common
# Transformations")


class CTM(NamedTuple):
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    @property
    def scale_x(self) -> float:
        return math.sqrt(pow(self.a, 2) + pow(self.b, 2))

    @property
    def scale_y(self) -> float:
        return math.sqrt(pow(self.c, 2) + pow(self.d, 2))

    @property
    def skew_x(self) -> float:
        return (math.atan2(self.d, self.c) * 180 / math.pi) - 90

    @property
    def skew_y(self) -> float:
        return math.atan2(self.b, self.a) * 180 / math.pi

    @property
    def translation_x(self) -> float:
        return self.e

    @property
    def translation_y(self) -> float:
        return self.f
