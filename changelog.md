# InveniaUtils

## Version 0.13.0

### Features

 * Support Lists in the Normalized Writer [!28](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/28)

## Version 0.12.0

### Features

 * Support len() operation on SeekableStreams. [!27](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/27)

## Version 0.11.1

### Fixes

 * Fix cleanup Pipeline step. [!26](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/26)

## Version 0.11.0

### Features

 * Add Decimal and date support to the normalized writer. [!25](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/25)
	
## Version 0.10.0

### Features

 * Update the `xlsutil` to auto detect the input file type when no file name is provided [!23](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/23)

## Version 0.9.0

### Features

 * Update the `xlsutil` to support accessing a sheet cell given a row and column number [!21](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/21)

## Version 0.8.0

### Features

 * Add utility for parsing both `xls` and `xlsx` files [!19](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/19)
 * Add support for writing to SeekableStreams [!18](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/18)

### Fixes

  * Don't use empty dicts as default args [!17](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/17)

## Version 0.7.0

### Features

  * Add custom logging handlers and formatters [!15](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/15)	

## Version 0.6.0

### Features

  * Decode Inf DatetimeRanges [!16](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/16)

## Version 0.5.0

### Features

  * Deploy releases to our private PyPI repo [!13](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/13), [!14](https://gitlab.invenia.ca/invenia/inveniautils/-/merge_requests/14)

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
