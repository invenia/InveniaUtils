# InveniaUtils

## Version 0.5.0

  * Deploy releases to our private PyPI repo [!13](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/13)

## Version 0.4.0

  * Implement stream.SeekableStream class.
    [!12](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/12)

## Version 0.3.1

  * Separate install and test requirements.
    [!9](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/9)

## Version 0.3.0

### Features

  * Adds a new function, `sort_key` for sorting `DatetimeRanges`.
    [!5](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/5)
  * Adds a new `size` method, to `DatetimeRanges` for getting a `timedelta` the length of a range, and implements `len` to get a ranges length in seconds.
    [!7](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/7)
  * Type hints have been added for all functions and methods in the `datetime_range` module.
    [!6](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/6), [!7](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/7)

### Deprecations & Planned Breaking Changes

  * The function for sorting `DatetimeRange` objects, `cmp_ranges` is being replaced by `sort_key`.
    `cmp_ranges` will be removed in `0.4.0`, as it has already been replaced in all projects that use InveniaUtils.
    [!5](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/5)
  * `Bound.valid` is being removed in `0.4.0`, as `Bound` is now an `IntEnum`, so checking whether a bound value is valid can now be done correctly.
    No real-world usage of this method currently exists.
    [!7](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/7)
  * `Bound` will remain an `IntEnum` for all `0.4` releases, but will be converted to an `Enum` no later than `1.0`.
     At least one minor release's notice will be given.
     Current usage of it being usable as an `int` is unknown.

## Version 0.2.0

  * Runs `black` against Python files [!2](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/2)
  * Generates documentation using sphinx [!2](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/2)
  * Adds a utility for parsing text from PDF files [!2](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/2)

## Version 0.1.1

  * Update setup.py to install required dependencies [!1](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/1)

## Version 0.1.0

  * First release as a standalone repository (previously part of Datafeeds [Retrievers](https://gitlab.invenia.ca/invenia/Datafeeds/Retrievers))
