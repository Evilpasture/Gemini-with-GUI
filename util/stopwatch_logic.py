import time


class Stopwatch:
    def __init__(self, root, output_display):
        self.root = root
        self.output_display = output_display

        # State variables
        self.running = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.timer = None

    @staticmethod
    def _format_time(time_in_seconds):
        total_milliseconds = int(time_in_seconds * 1000)

        milliseconds = total_milliseconds % 1000
        total_seconds = total_milliseconds // 1000

        seconds = total_seconds % 60
        minutes = total_seconds // 60

        # Return M:SS.ms (where ms is hundredths of a second)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds // 10:02d}"

    def _update(self):
        if self.running:
            self.elapsed_time = time.monotonic() - self.start_time
            self.output_display.config(text=self._format_time(self.elapsed_time))

            # recursive call to keep updating
            self.timer = self.root.after(50, self._update)

    def start(self):
        if not self.running:
            # Shift start_time forward so the elapsed calculation remains correct
            # even after a pause.
            self.start_time = time.monotonic() - self.elapsed_time
            self.running = True
            self._update()

    def stop(self):
        if self.running:
            if self.timer:
                self.root.after_cancel(self.timer)
            self.running = False

    def reset(self):
        if self.running:
            self.stop()

        self.elapsed_time = 0.0
        self.output_display.config(text=self._format_time(0.0))
