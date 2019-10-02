def full_class_name(x):
    return ".".join([
        x.__class__.__module__,
        x.__class__.__name__,
    ])
