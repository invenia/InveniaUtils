import os


def full_path(filename):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, filename)
