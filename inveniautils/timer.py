import sys
import time
from datetime import timedelta


class Timer(object):
    def __init__(self, start=False, timer=time):
        """
        Creates a timer object for timing python functions.

        :param start: (optional) starts the time right away.
        """
        self.started = None
        self.elapsed_at_stop = None
        self.timer = timer

        if start:
            self.start()

    @property
    def running(self):
        return self.started is not None

    @property
    def elapsed(self):
        """Returns the total elapsed time between when the timer was
        started to when it was stopped. If the timer is still running
        the elapsed time will be from started to now.
        """
        if self.running:
            return timedelta(seconds=self.timer.time() - self.started)
        else:
            return self.elapsed_at_stop

    def start(self):
        if not self.running:
            self.started = self.timer.time()
        else:
            raise ValueError("Must stop timer before starting.")

    def stop(self):
        if self.running:
            self.elapsed_at_stop = self.elapsed
            self.started = None
        else:
            raise ValueError("Must start timer before stopping.")

        return self.elapsed

    def tic(self):
        self.start()

    def toc(self):
        return self.stop()

    def __enter__(self):
        if not self.running:
            self.start()
        return self

    def __exit__(self, type, value, traceback):
        if self.running:
            self.stop()


class EstimatedTimeToCompletion(object):
    def __init__(self, total_iterations, timer=time):
        self.current_iteration = 0
        self.total_iterations = total_iterations
        self.timestamp = None
        self.elapsed = timedelta(0)
        self.last_display_length = 0
        self.timer = timer

    @classmethod
    def test(cls, iterations=120, interval=0.1, timer=None):
        import time
        if not timer:
            timer = time

        eta = cls(iterations, timer=timer)
        for i in range(iterations):
            eta.report()
            eta.timer.sleep(interval)

        return eta.final_report()

    def reset(self):
        self.timestamp = None
        self.elapsed = timedelta(0)

    def display(self, text):
        whitespace = ' ' * (self.last_display_length - len(text))

        sys.stdout.write('\r{}{}'.format(text, whitespace))
        sys.stdout.flush()

        self.last_display_length = len(text) - text.rfind('\n') - 1

    def report(self, current_iteration=None):
        now = self.timer.time()
        estimate = None

        if current_iteration is not None:
            self.current_iteration = current_iteration

        if self.timestamp:
            self.elapsed += timedelta(seconds=now - self.timestamp)
            time_per_iteration = self.elapsed // self.current_iteration
            remaining_iterations = (
                self.total_iterations - self.current_iteration
            )
            estimate = time_per_iteration * remaining_iterations

            self.display(
                'Remaining time {} {}'.format(
                    estimate,
                    remaining_iterations,
                )
            )

        # Bump current iteration if no iteration value is given.
        if current_iteration is None:
            self.current_iteration += 1

        self.timestamp = now

        return estimate

    def final_report(self):
        self.display(
            'Total runtime {} {}\n'.format(
                self.elapsed,
                self.total_iterations,
            )
        )

        return self.elapsed
