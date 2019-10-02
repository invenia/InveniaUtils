from collections import OrderedDict

from inveniautils.compat import cmp
from inveniautils.datetime_range import DatetimeRange


class Repetition(object):
    NATURAL = 0  # Output is not modified.
    PERSIST = 1  # Fall back to previous available occurrence.
    LAST = 2     # Only keep the last occurrence in all streams.
    # FIRST = 3    # Only keep the first occurrence in all streams.


# Works similarily to heapq.merge.
# http://docs.python.org/2/library/heapq.html#heapq.merge
def layered(
    iterables, cmp=cmp, blend=None, transform=None,
    repetition=Repetition.LAST, debug=False,
):
    """Combines multiple sorted iterables into a single iterator.
    Expects all iterables to be all ordered in the same way.

    iterables: an iterator containing iterators to be layered.
    cmp: (optional) the comparison function to use when comparing values.
    blend: (optional) a function which dictates how equivalent values
        should be combined.
    transform: (optional) a function which can adjust the values before
        blending but does not effect comparisons.
    repetition: (optional) a enumerated type which modifies the results
        when encountering repeated keys within the iterators.

    Note: Using a blend function that takes in an iterable simplifies
    the internal code and eliminates the need for transform but results
    in more complicated blending functions. Further work may be required
    """
    iterators = []
    for iterable in iterables:
        # Extract the iterator out of the object. aka. xrange
        iterators.append(iter(iterable))

    # Differentiates None from non-existent.
    null = object()

    element = {}       # The latest yielded value from each iterator.
    prev_element = {}  # The values that were previously contained in element.
    compound = {}      # Values to be blended.
    equivalent = []    # Identifies the earliest equal values within element.

    # Keep track of the original ordering of the iterators.
    ordering = list(iterators)

    # We'll remove iterators from this list as they complete.
    while iterators:

        # Determine the values that are equivalent within element.
        # Note copy the list so we can delete iterator during the loop.
        for iterator in list(iterators):

            # Update element with latest unused value from all iterators.
            if iterator not in element:
                try:
                    element[iterator] = next(iterator)
                except StopIteration:
                    iterators.remove(iterator)  # Avoid future processing.
                    continue

            # Skip processing on elements we've already found to be equivalent.
            # Note this code is strictly an optimization and could be
            # safely removed without changing the outcome.
            elif iterator in equivalent:
                if debug:
                    print(
                        "skip   {} {}".format(
                            ordering.index(iterator), element[iterator],
                        )
                    )
                continue

            if equivalent:
                comparison = cmp(
                    element[iterator],
                    element[equivalent[0]],
                )
            else:
                comparison = -1  # Force initialize equivalent.

            # Initialize or reset equivalent when the element
            # preceeds what is stored in equivalent.
            if comparison < 0:
                equivalent = []
                equivalent.append(iterator)

                if debug:
                    print(
                        "assign {} {}".format(
                            ordering.index(iterator), element[iterator],
                        )
                    )

            # Append the equivalent element.
            elif comparison == 0:
                equivalent.append(iterator)

                if debug:
                    print(
                        "append {} {}".format(
                            ordering.index(iterator), element[iterator],
                        )
                    )
            else:
                if debug:
                    print(
                        "ignore {} {}".format(
                            ordering.index(iterator), element[iterator],
                        )
                    )

        if debug:
            print(
                "equivalent {}\ncompound {}".format(
                    [element[i] for i in equivalent],
                    [compound[i] for i in ordering if i in compound],
                )
            )

        unite = False
        if compound and equivalent:
            # Equivalent elements are also equal to the compound.
            unite = cmp(
                next(iter(compound.values())),
                element[equivalent[0]],
            ) == 0

        # Forces initialization of compound.
        elif not compound:
            unite = True

        # Note: Updating "prev_element" can safely occur before the
        # persist code since we only modify values that will not be used.
        if unite:
            for iterator in equivalent:
                # Causes the next element to be pulled on the next iteration.
                value = element.pop(iterator)

                compound[iterator] = value
                prev_element[iterator] = value

            equivalent = []

            if debug:
                print(
                    "compound united {}".format(
                        [compound[i] for i in ordering if i in compound],
                    )
                )

            if repetition == Repetition.LAST:
                continue  # Skip to the beginning of the while.

        # Re-use previous values from iterators that are not currently
        # represented within "element".
        if repetition == Repetition.PERSIST:
            try:
                value = next(iter(compound.values()))
            except StopIteration:
                return

            for iterator in prev_element:
                # Skip iterators that are already represented.
                if iterator in compound:
                    continue

                # Only persist values that are equal to the "compound" values.
                comparison = cmp(prev_element[iterator], value)
                if comparison == 0:
                    compound[iterator] = prev_element[iterator]

                    if debug:
                        print(
                            "persist {} {}".format(
                                ordering.index(iterator), compound[iterator],
                            )
                        )

        # Perform post-processing on the compounded values.
        combined = null
        for iterator in ordering:
            if iterator not in compound:
                continue

            component = compound[iterator]

            # Modify the value.
            if transform is not None:
                component = transform(component)

            if blend is not None:
                # Combined values from the iterators that are equivalent.
                if combined is null:
                    combined = component

                    if debug:
                        print(
                            "blend start {} {}".format(
                                ordering.index(iterator), combined,
                            )
                        )
                else:
                    combined = blend(combined, component)

                    if debug:
                        print(
                            "blend {} {}".format(
                                ordering.index(iterator), combined,
                            )
                        )
            else:
                if combined is null:
                    combined = [component]
                else:
                    combined = combined + [component]

        # Will only yield a value here when blend is a function.
        if combined is not null:
            yield combined

        compound = {}


# itertools.groupby works in a similar fashion:
# http://docs.python.org/2/library/itertools.html#itertools.groupby
def aggregate(
    iterable, keys=None, aggregator=None, relevant=None, complete=None,
    relevancy_check=64, debug=False,
):
    """
    Aggregates the contents of an iterable. Works best if the iterable
    is sorted.

    keys: function which returns an iterable containing aggregate keys
        (in dictionary key format, ie. tuple with name/val) in which
        this element is a part of. Default is to treat the element as a key.
    aggregator: function which takes the aggregate key and the values
        associated with that key and combines them in some way. If something
        is wrong and the aggregate should be ignored return None. Default is to
        return the number of values associated with the key.
    relevant: function which checks an aggregate key against the current
        iterator's element to determine if the aggregate should be computed
        early. Default is to check if the aggregate key still a part of
        the keys produced by the current element.
    complete: function which determines if aggregate is complete. Useful for
        when you need an exact set of values to produce the aggregate. Ignored
        by default.
    """
    if keys is None:
        keys = lambda value: [value]
    if relevant is None:
        relevant = lambda key, element, element_keys: key in element_keys
    if aggregator is None:
        aggregator = lambda key, values: (yield key, len(values))

    # Note: In order to return results in order we'll probably have to
    # add a cmp function to tell what needs to be yielded first.

    # Will cause aggregates completed at the same to be yielded in the
    # order in which they were added to the cache.
    cache = OrderedDict()

    index = 0
    for element in iter(iterable):
        # Note: By far the slowest part of aggregation is calling the
        # keys function. Note that even without the internals of the
        # function just calling a function (lambda x: []) is 35x slower
        # than just inline code ([]).
        element_keys = list(keys(element))

        if debug and element_keys:
            print("Element ({}): {}".format(index, element))
            print("Element Keys:", element_keys)

        # Avoid checking for irrelevant cached data on every iteration
        # of the loop to improve performance. By reducing the amount of
        # calls we do to relevant() we can significantly improve
        # performance while non-significantly increasing memory usage.
        #
        # Test was performed on ordered 5-minute data making hourly
        # averages.
        #
        # #  Calls   Duration
        # -----------------------
        # 1  1383676 137.221 secs
        # 2   749640  79.935 secs
        # 4   433464  54.427 secs
        # 8   275376  40.765 secs
        # 16  196332  36.144 secs
        # 32  156804  30.674 secs
        # 64  137057  29.481 secs
        # Inf      0  29.327 secs

        def get_cmp_key(prime_kv_pairs):
            """A 'prime_kv_pairs' is the primary key(s) of a row of data. This
            is expected to be a list of 2-item tuples.
            Eg: [(k1,v1), (k2,v2), (k3,v3), (k4,v4)].
            This method takes [(k1,v1), (k2,v2)] and outputs [v1, v2].
            If the value is a DTR, the output will be set to DTR.start

            This method also handles the cases when 'prime_kv_pairs' is an
            OrderedDict({k1:v1, k2:v2, k3:v3, k4:v4}), or when it is of the
            form [(k1,v1), (v2), (k3,v3), v4], both these cases will produce
            the output [v1, v2, v3, v4], although these cases should not exist
            as all current use cases utilize the same keys() method to generate
            prime_kv_pairs, which will be in the form of [(k1,v1), (k2,v2),...]

            Note: The row_key is obtained from a row (dict) of data by calling
            the keys() function on it. The keys() function, as seen above, is
            passed to the parent function as an argument. Refer to:
            datafeeds.core.utils.aggregator.TimeSeriesAggregate.grouping()
            to view implementations of the keys() method.
            """
            keys = []
            if isinstance(prime_kv_pairs, (OrderedDict, dict)):
                for i in prime_kv_pairs:
                    v = prime_kv_pairs[i]
                    v = v.start if isinstance(v, DatetimeRange) else v
                    keys.append(v)
            elif isinstance(prime_kv_pairs, (tuple, list)):
                for i in prime_kv_pairs:
                    if isinstance(i, (tuple, list)):
                        if len(i) == 2:
                            v = i[1]
                        elif len(i) == 1:
                            v = i[0]
                        else:
                            raise ValueError(
                                "If the primary key's components are tuples, "
                                "it is expected to be of len==2 (key-value) "
                                "or of len==1 (value), found: {}.".format(i)
                            )
                    else:
                        v = i
                    val = v.start if isinstance(v, DatetimeRange) else v
                    keys.append(val)
            else:
                keys = prime_kv_pairs
            return keys

        if index % relevancy_check == 0:
            # Copy the keys so we can delete elements during the loop.
            for k in sorted(cache.keys(), key=get_cmp_key):
                # Note: A possible simiplified relevant call.
                # if relevant is not None and not relevant(k, element) \
                # or relevant is None and k not in element_keys:
                if not relevant(k, element, element_keys):
                    if debug:
                        print("Irrelevant ({}): {}".format(index, k))
                    aggregates = aggregator(k, cache.pop(k))

                    for aggregate in aggregates:
                        yield aggregate

        # Determine what aggregates the element is a part of.
        for k in element_keys:
            if k not in cache:
                cache[k] = []

            # Will append by reference when dealing with objects like
            # dicts.
            cache[k].append(element)

            # Check if an element is complete after a new element was
            # added to the cache.
            if complete is not None and complete(k, cache[k]):
                if debug:
                    print('Complete {}'.format(k))
                aggregates = aggregator(k, cache.pop(k))

                for aggregate in aggregates:
                    yield aggregate

        index += 1

    for k in sorted(cache.keys(), key=get_cmp_key):
        aggregates = aggregator(k, cache.pop(k))

        for aggregate in aggregates:
            yield aggregate


class UnorderedError(Exception):
    pass


def ensure_ordering(
    iterable, key=lambda k: k, cmp=cmp, unique=False, msg="",
):
    iterable = iter(iterable)
    try:
        element = next(iterable)
    except StopIteration:
        return

    # Pre-load previous_element to avoid additional checking on every
    # iteration. Additionally, also solves issue with iterator
    # containing None.
    yield element
    previous_element = element
    previous_element_key = key(element)

    for element in iterable:
        element_key = key(element)
        comparison = cmp(previous_element_key, element_key)

        # Useful to show the entire element rather than just the keys as
        # the keys don't give any context.
        if comparison > 0:
            raise UnorderedError(
                (
                    "Previous element is larger than current element. {}\n"
                    "Previous: {}\n"
                    "Current:  {}\n"
                    "Previous Key: {}\n"
                    "Current Key:  {}"
                ).format(
                    msg,
                    previous_element,
                    element,
                    previous_element_key,
                    element_key,
                )
            )
        elif unique and comparison == 0:
            raise UnorderedError(
                (
                    "Previous element is equivalent to the current element. "
                    "{}\n"
                    "Previous: {}\n"
                    "Current:  {}\n"
                    "Previous Key: {}\n"
                    "Current Key:  {}"
                ).format(
                    msg,
                    previous_element,
                    element,
                    previous_element_key,
                    element_key,
                )
            )

        yield element
        previous_element = element
        previous_element_key = element_key


def ensure_keys(iterable, expected, key=lambda k: k):
    for element in iterable:
        element_key = key(element)
        if element_key == expected:
            yield element
        else:
            raise ValueError(
                (
                    "Element key does not match expected:\n"
                    "Element:  {}\n"
                    "Expected: {}"
                ).format(
                    element_key,
                    expected,
                )
            )


def set_field(iterable, key, value):
    for element in iterable:
        element[key] = value
        yield element


def is_empty(iterable):
    try:
        next(iter(iterable))
    except StopIteration:
        return True  # First element threw exception StopIteration.
    else:
        return False  # First element exists.
