from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PresentValue:
    val: float
    n: int = 1
    i: float = 0.0

    def __str__(self):
        return str(self.val)

    @property
    def future_value(self):
        return round(self.val * (1 + self.i)**self.n, 2)

    @property
    def uniform_series(self):
        try:
            return round(self.val * (self.i*(1+self.i)**self.n / ((1 + self.i)**self.n - 1)), 2)
        except ZeroDivisionError:
            return 0

@dataclass
class FutureValue:
    val: float
    n: int = 1
    i: float = 0.0

    @property
    def uniform_series(self):
        try:
            return round(self.val * (self.i / ((1 + self.i)**self.n - 1)), 2)
        except ZeroDivisionError:
            return round(self.val / self.n, 2)

    def save_rate(self, date, period=30):
        if isinstance(period, int):
            period = timedelta(days=period)
        self.n = (date - datetime.now()) / period
        self.i /= (timedelta(days=365) / period)
        return round(self.uniform_series, 2)