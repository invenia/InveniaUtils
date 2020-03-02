import itertools
import logging
import operator
import unittest
import math
from datetime import datetime
from functools import partial
from types import GeneratorType

from inveniautils.compat import cmp
from inveniautils.iteration import (
    Repetition,
    UnorderedError,
    aggregate,
    ensure_ordering,
    layered,
    set_field,
    ensure_keys,
    is_empty,
)

from pytz import utc


class TestLayered(unittest.TestCase):
    def test_basic(self):
        test = [range(3, 9 + 1, 2), range(2, 8 + 1, 3)]
        expected = [[2], [3], [5, 5], [7], [8], [9]]

        result = layered(test, debug=True)
        self.assertTrue(isinstance(result, GeneratorType))

        # Ensure that results are from a generator.
        # Adapted from: http://stackoverflow.com/a/9983596
        null = object()
        for a, b in itertools.zip_longest(result, expected, fillvalue=null):
            self.assertEqual(a, b)

    def test_reverse(self):
        test = [range(9, 3 - 1, -2), range(8, 2 - 1, -3)]
        expected = [[9], [8], [7], [5, 5], [3], [2]]

        # Note: You need to explicitly tell layered about the reversed
        # ordering.
        result = layered(test, cmp=lambda x, y: cmp(y, x), debug=True)

        self.assertEqual(list(result), list(expected))

    def test_blend(self):
        test = [range(3, 9 + 1, 2), range(2, 8 + 1, 3)]
        expected = [2, 3, 5, 7, 8, 9]

        result = layered(test, blend=lambda x, y: x, debug=True)

        self.assertEqual(list(result), list(expected))

    def test_blend_unsorted(self):
        """
        Even though unsorted iterables are unsupported we should ensure
        that information is never lost.
        """
        test = [[1, 3, 5, 2, 4, 6], [1, 3, 5]]
        expected = [1, 3, 5, 2, 4, 6]

        result = layered(test, blend=lambda x, y: x, debug=True)

        self.assertEqual(list(result), list(expected))

    def test_none(self):
        test = [[None], [None]]
        expected = [[None, None]]

        result = layered(test, debug=True)
        self.assertEqual(list(result), list(expected))

    def test_persist(self):
        streams = [
            [(0, "A0"), (1, "A1"), (2, "A2")],
            [(0, "B0"), (1, "B1")],
            [(0, "C0"), (0, "C1"), (2, "C2"), (2, "C3")],
        ]
        expected = [
            (0, set(["A0", "B0", "C0"])),  # All streams combined together.
            (0, set(["A0", "B0", "C1"])),  # Fall-though of data.
            (1, set(["A1", "B1"])),  # Gaps in streams.
            (2, set(["A2", "C2"])),  # Early end of stream.
            (2, set(["A2", "C3"])),  # Fall-through at end of stream.
        ]

        compare = lambda x, y: cmp(x[0], y[0])

        def prepare(x):
            return x[0], set([x[1]])

        def blend(x, y):
            return x[0], x[1] | y[1]

        for test in itertools.permutations(streams):
            result = layered(
                test,
                cmp=compare,
                blend=blend,
                transform=prepare,
                repetition=Repetition.PERSIST,
                debug=True,
            )
            self.assertEqual(list(result), list(expected))

    def test_natural(self):
        streams = [
            [(0, "A0"), (1, "A1"), (2, "A2")],
            [(0, "B0"), (1, "B1")],
            [(0, "C0"), (0, "C1"), (2, "C2"), (2, "C3")],
        ]
        expected = [
            (0, set(["A0", "B0", "C0"])),  # All streams combined together.
            (0, set(["C1"])),  # No fall-though of data.
            (1, set(["A1", "B1"])),  # Gaps in streams.
            (2, set(["A2", "C2"])),  # Early end of stream.
            (2, set(["C3"])),  # No fall-through at end of stream.
        ]

        compare = lambda x, y: cmp(x[0], y[0])

        def prepare(x):
            return x[0], set([x[1]])

        def blend(x, y):
            return x[0], x[1] | y[1]

        for test in itertools.permutations(streams):
            result = layered(
                test,
                cmp=compare,
                blend=blend,
                transform=prepare,
                repetition=Repetition.NATURAL,
                debug=True,
            )
            self.assertEqual(list(result), list(expected))

    def test_last(self):
        streams = [
            [(0, "A0"), (1, "A1"), (2, "A2")],
            [(0, "B0"), (1, "B1")],
            [(0, "C0"), (0, "C1"), (2, "C2"), (2, "C3")],
        ]
        expected = [
            (0, set(["A0", "B0", "C1"])),  # All streams combined together.
            (1, set(["A1", "B1"])),  # Gaps in streams.
            (2, set(["A2", "C3"])),  # Early end of stream.
        ]

        compare = lambda x, y: cmp(x[0], y[0])

        def prepare(x):
            return x[0], set([x[1]])

        def blend(x, y):
            return x[0], x[1] | y[1]

        for test in itertools.permutations(streams):
            result = layered(
                test,
                cmp=compare,
                blend=blend,
                transform=prepare,
                repetition=Repetition.LAST,
                debug=True,
            )
            self.assertEqual(list(result), list(expected))

    # Feature currently not implemented.
    @unittest.expectedFailure
    def test_first(self):
        streams = [
            [(0, "A0"), (1, "A1"), (2, "A2")],
            [(0, "B0"), (1, "B1")],
            [(0, "C0"), (0, "C1"), (2, "C2"), (2, "C3")],
        ]
        expected = [
            (0, set(["A0", "B0", "C0"])),  # All streams combined together.
            (1, set(["A1", "B1"])),  # Gaps in streams.
            (2, set(["A2", "C2"])),  # Early end of stream.
        ]

        compare = lambda x, y: cmp(x[0], y[0])

        def prepare(x):
            return x[0], set([x[1]])

        def blend(x, y):
            return x[0], x[1] | y[1]

        for test in itertools.permutations(streams):
            result = layered(
                test,
                cmp=compare,
                blend=blend,
                transform=prepare,
                repetition=Repetition.FIRST,
                debug=True,
            )
            self.assertEqual(list(result), list(expected))
            break

    def test_dict(self):
        test = [
            [{"id": 1, "v1": 1}, {"id": 3, "v1": 3}, {"id": 4, "v2": 4.1}],
            [
                {"id": 1, "v1": float("Inf")},
                {"id": 2, "v1": 2, "v2": 2.1},
                {"id": 3, "v1": float("-Inf"), "v2": 3.1},
            ],
        ]
        expected = [
            {"id": 1, "v1": 1},
            {"id": 2, "v1": 2, "v2": 2.1},
            {"id": 3, "v1": 3, "v2": 3.1},
            {"id": 4, "v2": 4.1},
        ]

        result = layered(
            test,
            cmp=lambda x, y: cmp(x["id"], y["id"]),
            blend=lambda x, y: {**y, **x},
            debug=True,
        )

        self.assertEqual(list(result), list(expected))

    def test_dict_persist(self):
        test = [
            [{"id": 1, "a": 1}, {"id": 1, "a": 3}, {"id": 1, "a": 5}],
            [{"id": 1, "b": 2}, {"id": 2, "b": 4}, {"id": 3, "b": 6}],
            [{"id": 1, "c": 0.5}, {"id": 1, "c": 0.25}, {"id": 2, "c": 0.125}],
        ]
        expected = [
            {"id": 1, "a": 1, "b": 2, "c": 0.5},
            {"id": 1, "a": 3, "b": 2, "c": 0.25},
            {"id": 1, "a": 5, "b": 2, "c": 0.25},
            {"id": 2, "b": 4, "c": 0.125},
            {"id": 3, "b": 6},
        ]

        result = layered(
            test,
            cmp=lambda x, y: cmp(x["id"], y["id"]),
            blend=lambda x, y: {**x, **y},
            repetition=Repetition.PERSIST,
            debug=True,
        )

        self.assertEqual(list(result), list(expected))

    def test_real_persist(self):
        test = [
            [
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 5.9634,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 6.98593,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 5.9578,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.54455,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.37282,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.29223,
                },  # noqa: E501
            ],  # Ordering (contingency_name, constraint_name, target_date)
            [
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00052,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00784,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00063,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00773,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.0006,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00776,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.0006,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00776,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00067,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00769,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00071,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00765,
                },  # noqa: E501
            ],  # noqa. Ordering (contingency_name, constraint_name, target_date, node_name)
        ]
        expected = [
            {
                "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00052,
                "shadow_price": 5.9634,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00784,
                "shadow_price": 5.9634,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00063,
                "shadow_price": 6.98593,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00773,
                "shadow_price": 6.98593,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.0006,
                "shadow_price": 5.9578,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00776,
                "shadow_price": 5.9578,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.0006,
                "shadow_price": 7.54455,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00776,
                "shadow_price": 7.54455,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00067,
                "shadow_price": 7.37282,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00769,
                "shadow_price": 7.37282,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00071,
                "shadow_price": 7.29223,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00765,
                "shadow_price": 7.29223,
            },  # noqa: E501
        ]

        key = operator.itemgetter(
            "contingency_name", "constraint_name", "target_date"
        )  # noqa: E501
        result = layered(
            test,
            cmp=lambda x, y: cmp(key(x), key(y)),
            blend=lambda x, y: {**x, **y},
            repetition=Repetition.PERSIST,
        )

        self.assertEqual(list(result), list(expected))

    @unittest.expectedFailure
    def test_real_persist_inconsistent_ordering(self):
        test = [
            [
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 5.9634,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 6.98593,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 5.9578,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.54455,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.37282,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "shadow_price": 7.29223,
                },  # noqa: E501
            ],  # Ordering (contingency_name, constraint_name, target_date)
            [
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00052,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00063,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.0006,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.0006,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00067,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "ANACACHO_ANA",
                    "node_name": "ANACACHO_ANA",
                    "shift_factor": 0.00071,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00784,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00773,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00776,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00776,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00769,
                },  # noqa: E501
                {
                    "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                    "contingency_name": "SN_SAJO5",
                    "constraint_name": "LASPUL_RAYMND1_1",
                    "resource_name": "WOODWRD2_WOODWRD2",
                    "node_name": "WOO_WOODWRD2",
                    "shift_factor": -0.00765,
                },  # noqa: E501
            ],  # noqa. Ordering (contingency_name, constraint_name, node_name, target_date)
        ]
        expected = [
            {
                "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00052,
                "shadow_price": 5.9634,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00063,
                "shadow_price": 6.98593,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.0006,
                "shadow_price": 5.9578,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.0006,
                "shadow_price": 7.54455,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00067,
                "shadow_price": 7.37282,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "ANACACHO_ANA",
                "node_name": "ANACACHO_ANA",
                "shift_factor": 0.00071,
                "shadow_price": 7.29223,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 35, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00784,
                "shadow_price": 5.9634,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 40, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00773,
                "shadow_price": 6.98593,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 45, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00776,
                "shadow_price": 5.9578,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 50, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00776,
                "shadow_price": 7.54455,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 5, 55, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00769,
                "shadow_price": 7.37282,
            },  # noqa: E501
            {
                "target_date": datetime(2015, 3, 12, 6, 0, tzinfo=utc),
                "contingency_name": "SN_SAJO5",
                "constraint_name": "LASPUL_RAYMND1_1",
                "resource_name": "WOODWRD2_WOODWRD2",
                "node_name": "WOO_WOODWRD2",
                "shift_factor": -0.00765,
                "shadow_price": 7.29223,
            },  # noqa: E501
        ]

        key = operator.itemgetter(
            "contingency_name", "constraint_name", "node_name", "target_date"
        )  # noqa: E501
        result = layered(
            test,
            cmp=lambda x, y: cmp(key(x), key(y)),
            blend=lambda x, y: dict(y.items() + x.items()),
            repetition=Repetition.PERSIST,
        )

        self.assertEqual(list(result), list(expected))


class TestAggregate(unittest.TestCase):
    def test_basic(self):
        test = "AAAABBBCCD"
        expected = [("A", 4), ("B", 3), ("C", 2), ("D", 1)]

        result = aggregate(test, debug=True)
        self.assertEqual(list(result), list(expected))

    def test_average(self):
        test = [
            {"dt": 0, "n": 1, "v": 1},
            {"dt": 1, "n": 1, "v": 2},
            {"dt": 2, "n": 1, "v": 3},
            {"dt": 2, "n": 2, "v": 4},
        ]
        expected = [
            {"dt": 1, "n": 1, "v": 1.5},
            {"dt": 2, "n": 1, "v": 2.5},
            {"dt": 2, "n": 2, "v": 4},
        ]

        def average_grouping(row, average_dates, period):
            for dt in average_dates:
                if row["dt"] > dt - period and row["dt"] <= dt:
                    yield tuple({"dt": dt, "n": row["n"]}.items())

        def averager(identifier, rows, average_keys):
            result = dict(identifier)

            for k in average_keys:
                # Remove empty values.
                values = [r[k] for r in rows if r[k] is not None]

                if len(values) == 0:
                    result[k] = None
                else:
                    result[k] = sum(values) / len(values)  # Floating division

            yield result

        result = aggregate(
            test,
            partial(average_grouping, average_dates=[1, 2], period=2),
            partial(averager, average_keys=["v"]),
            debug=True,
        )

        self.assertEqual(list(result), list(expected))

    @unittest.expectedFailure
    def test_mixing(self):
        test = [
            {"a": 1, "b": 1, "v": 1},
            {"a": 1, "b": 2, "v": 2},
            {"a": 2, "b": 1, "v": 3},
            {"a": 2, "b": 2, "v": 4},
        ]
        expected = [
            (("a", 1), 2),
            (("b", 1), 2),
            (("a", 2), 2),
            (("b", 2), 2),
        ]  # Not sure if this is exactly what should be returned.

        def grouping(row):
            return [("a", row["a"]), ("b", row["b"])]

        result = aggregate(test, grouping, debug=True)
        self.assertEqual(list(result), list(expected))

    def test_sets(self):
        test = [
            {"dt": 0, "n": 1, "v": 1},
            {"dt": 0, "n": 3, "v": 2},
            {"dt": 1, "n": 2, "v": 3},
            {"dt": 2, "n": 1, "v": 4},
            {"dt": 2, "n": 2, "v": 5},
            {"dt": 2, "n": 3, "v": 6},
        ]
        node_to_agg = {1: {"a": 0.5, "b": 0.25}, 2: {"b": 0.75}, 3: {"a": 0.5}}
        agg_to_node = {"a": {1: 0.5, 3: 0.5}, "b": {1: 0.25, 2: 0.75}}
        expected = [
            {"dt": 0, "agg": "a", "v": 1.5},
            {"dt": 0, "agg": "b", "v": 0.25},
            {"dt": 1, "agg": "b", "v": 2.25},
            {"dt": 2, "agg": "b", "v": 4.75},
            {"dt": 2, "agg": "a", "v": 5},
        ]

        def average_grouping(row):
            node = row["n"]
            if node in node_to_agg:
                for agg in node_to_agg[node].keys():
                    yield tuple({"dt": row["dt"], "agg": agg}.items())

        def average_relevant(identifier, element, element_keys):
            identifier = dict(identifier)
            return identifier["dt"] == element["dt"]

        def average_complete(identifier, rows):
            identifier = dict(identifier)
            nodes = agg_to_node[identifier["agg"]].keys()
            return set(nodes) == set(r["n"] for r in rows)

        def averager(identifier, rows, average_keys):
            result = dict(identifier)

            for k in average_keys:
                # Remove empty values.
                values = []
                for row in rows:
                    if row[k] is not None:
                        weight = node_to_agg[row["n"]][result["agg"]]
                        values.append(row[k] * weight)

                if len(values) == 0:
                    result[k] = None
                else:
                    result[k] = sum(values)

            yield result

        result = aggregate(
            test,
            keys=average_grouping,
            aggregator=partial(averager, average_keys=["v"]),
            relevant=average_relevant,
            complete=average_complete,
            relevancy_check=1,
            debug=True,
        )

        self.assertEqual(list(result), list(expected))

    def test_release_dates(self):
        test = [
            {"dt": 0, "rd": 1, "n": "a", "v": 0.011},
            {"dt": 0, "rd": 1, "n": "b", "v": 0.012},
            {"dt": 0, "rd": 2, "n": "b", "v": 0.022},
            {"dt": 0, "rd": 3, "n": "a", "v": 0.031},
            {"dt": 1, "rd": 2, "n": "b", "v": 0.122},
            {"dt": 1, "rd": 2, "n": "a", "v": 0.121},
            {"dt": 1, "rd": 3, "n": "a", "v": 0.131},
            {"dt": 2, "rd": 3, "n": "a", "v": 0.231},
        ]  # Ordering (dt, rd)
        expected = [
            {"dt": 0, "rd": 1, "n": "a", "v": [0.011]},
            {"dt": 0, "rd": 2, "n": "a", "v": [0.011, 0.121]},
            {"dt": 0, "rd": 3, "n": "a", "v": [0.031, 0.131]},
            {"dt": 0, "rd": 1, "n": "b", "v": [0.012]},
            {"dt": 0, "rd": 2, "n": "b", "v": [0.022, 0.122]},
            {"dt": 2, "rd": 3, "n": "a", "v": [0.231]},
        ]

        def average_grouping(row):
            yield tuple({"dt": row["dt"] - (row["dt"] % 2), "n": row["n"]}.items())

        def averager(identifier, rows, average_keys):
            # Determine all possible release dates
            all_release_dates = set(row["rd"] for row in rows)
            versions = {release_date: [] for release_date in all_release_dates}

            # Isolate the rows for each possible release dates
            rows.reverse()
            for row in rows:
                for ad in all_release_dates:
                    if row["rd"] <= ad and (
                        not versions[ad] or row["dt"] != versions[ad][-1]["dt"]
                    ):  # noqa: E501
                        versions[ad].append(row)

            for ad in sorted(versions.keys()):
                result = dict(identifier)
                result["rd"] = ad
                rows = versions[ad]
                rows.reverse()

                # Perform aggregation for each version
                for k in average_keys:
                    result[k] = [r[k] for r in rows]
                yield result

        result = aggregate(
            test, average_grouping, partial(averager, average_keys=["v"]), debug=True
        )

        self.assertEqual(list(result), list(expected))


class TestEnsureOrdering(unittest.TestCase):
    def test_basic(self):
        dates = [
            datetime(2016, 1, 1),
            datetime(2016, 1, 2),
            datetime(2016, 1, 3),
            datetime(2016, 1, 5),
            datetime(2016, 1, 4),
        ]

        iterable = ensure_ordering(dates)
        for i in range(len(dates) - 1):
            self.assertEqual(next(iterable), dates[i])

        with self.assertRaises(UnorderedError):
            next(iterable)

    def test_ordered(self):
        dates = [
            datetime(2016, 1, 1),
            datetime(2016, 1, 2),
            datetime(2016, 1, 3),
            datetime(2016, 1, 4),
            datetime(2016, 1, 5),
        ]

        iterable = ensure_ordering(dates)
        self.assertEqual(list(iterable), dates)

    def test_unique(self):
        dates = [
            datetime(2016, 1, 1),
            datetime(2016, 1, 2),
            datetime(2016, 1, 4),
            datetime(2016, 1, 4),
            datetime(2016, 1, 5),
        ]

        self.assertRaises(
            UnorderedError, lambda: list(ensure_ordering(dates, unique=True))
        )


class TestSetField(unittest.TestCase):
    def test_basic(self):
        values = [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}]

        actuals = set_field(values, "key", "value")

        for value in values:
            actual = next(actuals)
            self.assertEqual(actual[list(value.keys())[0]], list(value.values())[0])
            self.assertEqual(actual["key"], "value")


class TestEnsureKeys(unittest.TestCase):
    def test_ensure_keys_valid(self):
        expected = [55, 100, 130, 110, 60]
        keyfunc = lambda n: math.floor(math.log(n))

        self.assertEqual(list(ensure_keys(expected, 4, keyfunc)), expected)

    def test_ensure_keys_invalid(self):
        num = [1]

        self.assertRaises(ValueError, lambda: list(ensure_keys(num, 2)))


class TestIsEmpty(unittest.TestCase):
    def test_is_empty(self):
        self.assertTrue(is_empty([]))
        self.assertTrue(is_empty({}))
        self.assertFalse(is_empty([1]))
        self.assertFalse(is_empty({"a": 1}))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
