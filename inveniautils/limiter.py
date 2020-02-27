import logging
import time
from collections import namedtuple
from datetime import datetime, timedelta

from inveniautils.dates import utc

logger = logging.getLogger(__name__)
Status = namedtuple("Status", ["reported", "success"])

# timedelta will overflow before sys.max is reached so timedelta.max is used
MAX_SECONDS = timedelta.max.total_seconds()


class StatusHistory(object):
    def __init__(self, limit=None):
        self.limit = limit
        self._status = []

        # Last successful/failed statuses. These may be statuses no
        # longer in the status list.
        self._last_success_status = None
        self._last_failure_status = None

    @property
    def status(self):
        return self._status

    def add(self, status):
        latest_status = self._status[-1] if self._status else None

        # Ensure that status history is in chronological order.
        if latest_status and latest_status.reported > status.reported:
            raise ValueError(
                "New status records must occur after the last stored status"
            )

        self._status.append(status)

        if status.success is True:
            self._last_success_status = status
        elif status.success is False:
            self._last_failure_status = status

        if self.limit and len(self._status) > self.limit:
            self._status.pop(0)

    def last_reported(self, successful=None):
        if successful is True:
            status = self._last_success_status
        elif successful is False:
            status = self._last_failure_status
        elif self._status:
            status = self._status[-1]
        else:
            status = None

        if status is not None:
            return status.reported
        else:
            return None


class Limiter(object):
    def __init__(
        self, initial_interval=0, min_interval=None, since_success=False, debug=False
    ):
        # The smallest allowed interval. Needs to be assigned prior to
        # interval assignment.
        self.min_interval = min_interval if min_interval is not None else 1

        # The amount of time to wait between status reports.
        self.interval = initial_interval

        # Track when statuses were reported and if they passed.
        if debug:
            self.history = StatusHistory()
        else:
            self.history = StatusHistory(limit=3)

        # The smallest duration of time between two reports in which
        # a successful status occurred. Periodically reset.
        self.min_success_delta = None

        # The largest duration of time between two reports in which
        # a failed status occurred. Periodically reset.
        self.max_failure_delta = None

        # A stable system means that the used interval doesn't change
        # between successful status reports.
        self.stable = False

        # The interval used when system became stable.
        self.stable_interval = None

        # Allows the system to adjust at a slower rate allowing us to
        # not bound around too much when closing in on the optimal
        # interval.
        self.fine_tuning = False

        # Increment to use when performing the geometric progression.
        self.adjustment = 0

        # Intervals should be calculated since the last success and not
        # since the last status report.
        self.since_success = since_success

        # The last known interval that succeeded/failed.
        self.success_interval = None
        self.failure_interval = None

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, duration):
        # Restrict numeric values to be positive.
        if duration is not None and duration < 0:
            raise ValueError("Interval must be positive.")

        # Round the duration up to the next min_interval.
        if self.min_interval is not None:
            remainder = duration % self.min_interval
            duration -= remainder  # Round down

            # Round up and make sure we don't have the duration set to 0.
            if remainder > 0 or duration == 0:
                duration += self.min_interval

        self._interval = duration

    @property
    def min_success_delta(self):
        return self._min_success_delta

    @min_success_delta.setter
    def min_success_delta(self, duration):
        """
        Only allows the min_success_delta property to be a smaller
        positive value or None.
        """

        # Restrict numeric values to be positive.
        if duration is not None and duration < 0:
            raise ValueError("Interval must be positive.")

        smallest = getattr(self, "_min_success_delta", None)
        if duration is None or smallest is None or duration < smallest:
            self._min_success_delta = duration

            if duration is not None:
                self.success_interval = duration

    @property
    def max_failure_delta(self):
        return self._max_failure_delta

    @max_failure_delta.setter
    def max_failure_delta(self, duration):
        """
        Only allows the max_failure_delta property to be a larger
        positive value or None.
        """

        # Restrict numeric values to be positive.
        if duration is not None and duration < 0:
            raise ValueError("Interval must be positive.")

        largest = getattr(self, "_max_failure_delta", None)
        if duration is None or largest is None or duration > largest:
            self._max_failure_delta = duration

            if duration is not None:
                self.failure_interval = duration

    def waited(self, reported=None):
        if self.since_success:
            last_reported = self.history.last_reported(successful=True)
        else:
            last_reported = self.history.last_reported()

        if last_reported is None:
            return None

        if reported is None:
            reported = datetime.now(utc)

        duration = reported - last_reported

        if duration is not None and duration < timedelta(0):
            raise ValueError("Current time is prior to the last report time")

        duration = int(duration.total_seconds())

        return duration

    def delay(self, reported=None):
        waited = self.waited(reported)
        interval = self.interval

        if interval is not None and waited is not None:
            delay = interval - waited
        else:
            delay = 0

        return delay if delay >= 0 else 0

    def throttle(self, now=None):
        delay = self.delay(now)

        if delay > 0:
            logger.info("Sleeping for {} seconds.".format(delay))
            time.sleep(delay)

    def status(self, success, reported=None):
        # Allow for overwritting the reported time for slow status
        # reports and for testing purposes.
        if reported is None:
            reported = datetime.now(utc)

        # Make sure we calculate the delta before adding the new status.
        delta = self.waited(reported)

        self.history.add(Status(reported, success))

        if success:
            self.min_success_delta = delta
        else:
            self.max_failure_delta = delta

        attempted_interval = self.interval
        next_interval = None
        search_type = "U"  # "Unknown"

        success_history = [status.success for status in self.history.status[-3:]]

        # Mark system as unstable if we have 2 sequential failures.
        if success_history[-2:] == [False, False]:
            self.stable = False

        # Cancel fine-tuning if we have 3 sequential failures or if
        # we are stable and we are not seeing T F T...
        # if success_history[-4:] == [False, False, False, False] or self.stable and success_history[-4:] == [True, True, True, True]:  # noqa: E501
        # if success_history[-3:] == [False, False, False] or self.stable and success_history[-3:] == [True, True, True]:  # noqa: E501
        #     self.fine_tuning = False

        # Works well for larger min_intervals but not for smaller.
        if (
            delta is not None
            and self.stable_interval is not None
            and delta >= self.stable_interval * 2
        ):  # noqa: E501
            self.fine_tuning = False

        if success and self.stable and success_history[-2:] == [False, True]:
            self.stable_interval = attempted_interval
        elif success and not self.stable and self.stable_interval is not None:
            next_interval = self.stable_interval
            self.stable_interval = None

        if success_history[-3:] == [True, False, True]:
            self.stable = True

        if (
            next_interval is None
            and self.min_success_delta is not None
            and self.max_failure_delta is not None
        ):  # noqa: E501
            self.adjustment = 0  # Reset

            # The smallest success interval should always be larger than
            # the largest failure interval.
            if (
                self.min_success_delta - self.max_failure_delta > self.min_interval
            ):  # noqa: E501
                low = self.max_failure_delta
                high = self.min_success_delta

                # Use the mid-point to hone in on the optimal interval.
                # Note: The result of round will always be an integer but is
                # retuned as a float. The casting ensures that when both
                # min and max are integers an integer is returned.
                next_interval = low + int(round((high - low) / 2))

                search_type = "B"  # "Binary"
            else:
                # Reset one of the boundaries when they approach each other.
                if success:
                    self.max_failure_delta = None
                    self.fine_tuning = True
                else:
                    self.min_success_delta = None

                search_type = "R"  # "Reset"

        # Use a geometric progression to find our initial boundaries.
        if next_interval is None and (
            self.min_success_delta is None or self.max_failure_delta is None
        ):  # noqa: E501
            adjustment = self.adjustment

            if self.max_failure_delta and adjustment <= 0:
                adjustment = self.min_interval  # Increase when invalid.

            elif self.min_success_delta and adjustment >= 0:
                adjustment = -self.min_interval  # Reduce when valid.

            elif not self.fine_tuning:
                # an integer can grow too large for timedelta
                # which is used later in logging.debug
                if abs(adjustment) < MAX_SECONDS // 2:
                    adjustment *= 2

            # Only set the next_interval if the user waited long enough
            # between status reports.
            if delta is not None and delta >= attempted_interval:
                next_interval = attempted_interval + adjustment
                self.adjustment = adjustment
                search_type = "G"  # "Geometric"
            else:
                next_interval = attempted_interval
                search_type = "P"  # "Persist"

        self.interval = max(next_interval, self.min_interval)
        # calculate the effective actual adjustment, and store that.
        # avoids huge unrealistic adjustments in output, causing
        # exceptions int he formatting code
        if next_interval < self.min_interval:
            self.adjustment = attempted_interval - self.interval

        if logger.isEnabledFor(logging.DEBUG):

            def format_seconds(num):
                if num is None:
                    return "?"
                elif num < 0:
                    return "-{}".format(timedelta(seconds=-num))
                else:
                    return "{}".format(timedelta(seconds=num))

            logger.debug(
                "{} "
                "delta: {:>3} "
                "attempted_interval: {:>3} "
                "failure_interval: {:>3} "
                "success_interval: {:>3} "
                "next_interval: {:>3} "
                "success: {} "
                "type: {} "
                "adjustment {} "
                "stable: {} "
                "tune: {} ".format(
                    reported,
                    format_seconds(delta),
                    format_seconds(attempted_interval),
                    format_seconds(self.max_failure_delta),
                    format_seconds(self.min_success_delta),
                    format_seconds(next_interval),
                    "T" if success else "F",
                    search_type,
                    str(format_seconds(self.adjustment)),
                    # self.num_stable if self.num_stable is not None else '?',
                    "T" if self.stable else "F",
                    "T" if self.fine_tuning else "F",
                )
            )


class StaticLimiter(object):
    """A much simpler limiter which enforces a minimum interval.

    Maybe this should be a sibling of Limiter.

    Note that this does not care about status or results.
    """

    def __init__(self, interval=None):
        self._interval = interval
        self._last_called = None

    def throttle(self):
        if self._last_called is None:
            self._last_called = datetime.now(utc)
        elif self._interval is not None:
            now_time = datetime.now(utc)

            diff = (now_time - self._last_called).total_seconds()
            delay = self._interval - diff
            if delay > 0:
                logger.info("Sleeping for {} seconds.".format(delay))
                time.sleep(delay)
                return delay
        return 0

    def record_request(self):
        self._last_called = datetime.now(utc)

    def status(self, *args, **kwargs):
        """For API compatibility with Limiter
        """
        self.record_request()
