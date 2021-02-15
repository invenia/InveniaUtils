import math
from itertools import repeat


def angle_mean_radians(angles, weights=repeat(1)):
    return (
        math.atan2(
            math.fsum(math.sin(a) * w for a, w in zip(angles, weights))
            / len(angles),  # noqa
            math.fsum(math.cos(a) * w for a, w in zip(angles, weights))
            / len(angles),  # noqa
        )
        % (math.pi * 2)
    )


def angle_mean_degrees(angles, weights=repeat(1)):
    return math.degrees(
        angle_mean_radians([math.radians(angle) for angle in angles], weights)
    )


def mean(vals):
    return sum(vals) / len(vals)


def weighted_mean(vals, weights):
    return sum(v * w for v, w in zip(vals, weights)) / sum(weights)


class RoundingMode(object):
    UP = 0
    DOWN = 1
    TO_ZERO = 2
    FROM_ZERO = 3
    NEAREST_TIES_UP = 4
    NEAREST_TIES_FROM_ZERO = 5


def round_to(value, interval, mode=RoundingMode.NEAREST_TIES_FROM_ZERO):
    """
    Rounds to the value a number divisible by the interval.
    """
    interval = abs(interval)
    remainder = math.fmod(value, interval)
    value = value - remainder  # Rounded to zero
    # Apply rounding modes
    if mode == RoundingMode.NEAREST_TIES_FROM_ZERO:
        if remainder > 0 and remainder >= interval / 2.0:
            value += interval
        elif remainder < 0 and remainder <= -interval / 2.0:
            value -= interval
    elif mode == RoundingMode.NEAREST_TIES_UP:
        if remainder > 0 and remainder >= interval / 2.0:
            value += interval
        elif remainder < 0 and remainder < -interval / 2.0:
            value -= interval
    elif mode == RoundingMode.UP:
        if remainder > 0:
            value += interval
    elif mode == RoundingMode.DOWN:
        if remainder < 0:
            value -= interval
    elif mode == RoundingMode.TO_ZERO:
        pass
    elif mode == RoundingMode.FROM_ZERO:
        if remainder > 0:
            value += interval
        elif remainder < 0:
            value -= interval

    return value
