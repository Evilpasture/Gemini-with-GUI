import time


class _TimeBase:
    """Base class for time-related components (Stopwatch and Timer).
    Handles shared logic like initialization, time formatting, and stopping the loop."""

    def __init__(self, root, output_display):
        self.root = root
        self.output_display = output_display

        # Shared state variables
        self.running = False
        self.timer = None

        # elapsed_time will mean different things in subclasses:
        # Stopwatch: Time counted up
        # Timer: Time counted down (duration elapsed)
        self.elapsed_time = 0.0

    @staticmethod
    def _format_time(time_in_seconds):
        """Formats time (float) into M:SS.hh string."""
        if time_in_seconds < 0:
            time_in_seconds = 0.0  # Prevent negative display

        total_milliseconds = int(time_in_seconds * 1000)

        milliseconds = total_milliseconds % 1000
        total_seconds = total_milliseconds // 1000

        seconds = total_seconds % 60
        minutes = total_seconds // 60

        # Return M:SS.ms (where ms is hundredths of a second)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds // 10:02d}"

    def stop(self):
        """Stops the timing loop and sets running state to False."""
        if self.running:
            if self.timer:
                self.root.after_cancel(self.timer)
            self.running = False

class Stopwatch(_TimeBase):
    """Stopwatch utility designed for use within Tkinter"""

    def __init__(self, root, output_display):
        super().__init__(root, output_display)  # Initialize the base class
        # start_time is only needed for the monotonic calculation
        self.start_time = 0.0

    def _update(self):
        if self.running:
            # UNIQUE LOGIC: Calculate elapsed time counting UP
            self.elapsed_time = time.monotonic() - self.start_time
            self.output_display.config(text=self._format_time(self.elapsed_time))

            # recursive call to keep updating
            self.timer = self.root.after(50, self._update)

    def start(self):
        if not self.running:
            # UNIQUE LOGIC: Resume from where it left off (elapsed_time)
            self.start_time = time.monotonic() - self.elapsed_time
            self.running = True
            self._update()

    def reset(self):
        self.stop()  # Inherited from _TimeBase
        self.elapsed_time = 0.0
        self.output_display.config(text=self._format_time(0.0))


class Timer(_TimeBase):
    def __init__(self, root, output_display, total_duration_seconds=300):
        super().__init__(root, output_display)  # Initialize the base class

        # UNIQUE STATE: The total duration to count down from
        self.total_duration = total_duration_seconds
        self.start_time = 0.0

        # Initial display
        self.output_display.config(text=self._format_time(self.total_duration))

    def _update(self):
        if self.running:
            # UNIQUE LOGIC: Calculate time remaining
            time_since_start = time.monotonic() - self.start_time
            self.elapsed_time = time_since_start
            time_remaining = self.total_duration - self.elapsed_time

            if time_remaining <= 0:
                self.elapsed_time = self.total_duration
                self.stop()  # Inherited from _TimeBase
                self.output_display.config(text=self._format_time(0.0))
                return

            self.output_display.config(text=self._format_time(time_remaining))
            self.timer = self.root.after(50, self._update)

    def start(self):
        # Prevent starting if already finished counting down
        if not self.running and self.elapsed_time < self.total_duration:
            # UNIQUE LOGIC: Resume from where it left off (elapsed_time)
            self.start_time = time.monotonic() - self.elapsed_time
            self.running = True
            self._update()

    def reset(self):
        self.stop()  # Inherited from _TimeBase
        self.elapsed_time = 0.0
        # Reset display to the original total duration
        self.output_display.config(text=self._format_time(self.total_duration))

