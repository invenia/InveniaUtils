def float_to_decimal_str(f: float) -> str:
    """
    Convert the given float to a string without resorting to scientific
    notation

    Found code here https://stackoverflow.com/a/38983595/4487518

    Args:
        f: A floating point number

    Returns:
        A string, without scientific notation, that representing the input float
    """
    float_string = repr(f)
    # detect scientific notation
    if "e" in float_string:
        digits, exp = float_string.split("e")
        digits = digits.replace(".", "").replace("-", "")
        exp = int(exp)
        sign = "-" if f < 0 else ""

        if exp > 0:
            # minus the digits after the decimal point in scientific notation
            zero_padding = "0" * (abs(int(exp)) - len(digits) + 1)
            float_string = "{}{}{}.0".format(sign, digits, zero_padding)
        else:
            # minus 1 for decimal point in the sci notation
            zero_padding = "0" * (abs(int(exp)) - 1)
            float_string = "{}0.{}{}".format(sign, zero_padding, digits)

    return float_string
