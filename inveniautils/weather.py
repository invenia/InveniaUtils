import math
import pint

ureg = pint.UnitRegistry()
Q_ = ureg.Quantity


def dewpoint(
    dry_bulb,  # celsius
    rel_humidity=None,  # percent (between 0 and 1)
    wet_bulb=None,  # celsius
    pressure=None,  # kiloPascals
    elevation=None,  # metres
):
    """Calculates dewpoint.

    Returns dewpoint based on either dry bulb temprature and
    relative humidity or dry bulb temperature, wet bulb temperature,
    and elevation or pressure.

    :param dry_bulb: float
    :param rel_humidity: float or None
    :param wet_bulb: float or None
    :param pressure: float or None
    :param elevation: float or None
    :rtype : float
    """
    b = None

    if rel_humidity is not None:
        b = (math.log(rel_humidity) + 17.27 * dry_bulb / (237.3 + dry_bulb)) / 17.27
    elif pressure is not None or elevation is not None:
        if pressure is None:
            pressure = barometric_pressure(elevation)

        ew = 6.108 * math.exp(17.27 * wet_bulb / (237.3 + wet_bulb))

        e = ew - (0.00066 * (1 + 0.00115 * wet_bulb) * (dry_bulb - wet_bulb) * pressure)

        b = math.log(e / 6.108) / 17.27

    if b is None:
        raise RuntimeError("Insufficient data to calculate dewpoint.")

    return 237.3 * b / (1 - b)


def dewpoint_si(
    dry_bulb,  # Kelvin
    rel_humidity=None,  # percent (between 0 and 1)
    wet_bulb=None,  # Kelvin
    pressure=None,  # Pascals
    elevation=None,  # metres
):
    dry_bulb = Q_(dry_bulb, ureg.degK).to(ureg.degC).magnitude

    if wet_bulb is not None:
        wet_bulb = Q_(wet_bulb, ureg.degK).to(ureg.degC).magnitude

    if pressure is not None:
        pressure = (pressure * ureg.pascals).to(ureg.kilopascals).magnitude

    dp = dewpoint(
        dry_bulb,
        rel_humidity=rel_humidity,
        wet_bulb=wet_bulb,
        pressure=pressure,
        elevation=elevation,
    )

    return Q_(dp, ureg.degC).to(ureg.degK).magnitude


def barometric_pressure(elevation):
    """Returns pressure in kPa from elevation in metres

    :param elevation: float
    :rtype : float
    """
    return 101.3 * (((293 - (0.0065 * elevation)) / 293) ** 5.26)
