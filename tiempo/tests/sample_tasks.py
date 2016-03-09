def some_callable(*args, **kwargs):
    return args, kwargs


def some_callable_that_raises_an_error(*args, **kwargs):
    raise RuntimeError('This is an intentionally generated error.')