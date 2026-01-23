# argus/utils/clock.py
"""
Time abstraction utilities for ARGUS.

Provides injectable clock interfaces to avoid scattered datetime.now() calls
and enable deterministic time in tests.

Classes:
    Clock: Protocol defining the time provider interface.
    SystemClock: Production clock using system time.
    FrozenClock: Test clock fixed at a specific moment.
    OffsetClock: Decorator applying a constant offset to another clock.
    Stopwatch: Monotonic duration measurement.
    Timer: Context manager for timing code blocks.

Example:
    >>> clock = SystemClock()
    >>> with Timer(clock=clock, label='data_load') as timer:
    ...     load_data()
    >>> logger.info('Loaded in %.3fs', timer.elapsed_seconds)
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol, Self, runtime_checkable

__all__: list[str] = [
    'Clock',
    'FrozenClock',
    'OffsetClock',
    'Stopwatch',
    'SystemClock',
    'Timer',
]

logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# Clock Protocol
# =============================================================================


@runtime_checkable
class Clock(Protocol):
    """
    Interface for time providers in ARGUS.

    Design Goals:
        - Centralize time access (no scattered datetime.now() calls).
        - Enable deterministic time in tests.
        - Enforce timezone-aware UTC timestamps internally.

    All implementations must return timezone-aware UTC datetimes.
    """

    def now_utc(self) -> datetime:
        """
        Return the current time as a timezone-aware UTC datetime.

        Returns:
            Timezone-aware datetime in UTC.
        """
        ...

    def today_utc(self) -> date:
        """
        Return today's date in UTC.

        Returns:
            Current UTC date.
        """
        ...

    def monotonic_seconds(self) -> float:
        """
        Return a monotonic timestamp for duration measurement.

        Monotonic clocks are unaffected by NTP adjustments or DST changes,
        making them suitable for measuring elapsed time.

        Returns:
            Monotonic time in seconds.
        """
        ...


# =============================================================================
# Clock Implementations
# =============================================================================


@dataclass(frozen=True, slots=True)
class SystemClock:
    """
    Production clock backed by system wall-clock and monotonic timer.

    Returns timezone-aware UTC datetimes. This is the default clock
    for production use.
    """

    def now_utc(self) -> datetime:
        """Return current UTC time."""
        return datetime.now(tz=UTC)

    def today_utc(self) -> date:
        """Return current UTC date."""
        return self.now_utc().date()

    def monotonic_seconds(self) -> float:
        """Return monotonic time using perf_counter."""
        return time.perf_counter()


class FrozenClock:
    """
    Deterministic clock for tests and reproducible runs.

    Starts at a fixed UTC datetime and only advances when explicitly
    mutated via advance() or set_time().

    Attributes:
        _current_time_utc: The frozen wall-clock time.
        _current_monotonic_seconds: The frozen monotonic counter.

    Example:
        >>> clock = FrozenClock(start_time_utc=datetime(2026, 1, 23, 12, tzinfo=UTC))
        >>> clock.now_utc()
        datetime.datetime(2026, 1, 23, 12, 0, tzinfo=datetime.timezone.utc)
        >>> clock.advance(timedelta(hours=1))
        >>> clock.now_utc().hour
        13

    Note:
        Not thread-safe. Keep usage test-scoped or wrap externally.
    """

    __slots__ = ('_current_monotonic_seconds', '_current_time_utc')

    def __init__(
        self,
        *,
        start_time_utc: datetime,
        start_monotonic_seconds: float = 0.0,
    ) -> None:
        """
        Initialize a frozen clock.

        Args:
            start_time_utc: Initial time (must be timezone-aware UTC).
            start_monotonic_seconds: Initial monotonic value (non-negative).

        Raises:
            ValueError: If start_time_utc is naive or not UTC.
            ValueError: If start_monotonic_seconds is negative.
        """
        if start_time_utc.tzinfo is None:
            raise ValueError('start_time_utc must be timezone-aware (UTC).')
        if start_time_utc.tzinfo is not UTC:
            raise ValueError('start_time_utc must use datetime.UTC.')
        if start_monotonic_seconds < 0.0:
            raise ValueError('start_monotonic_seconds must be non-negative.')

        self._current_time_utc: datetime = start_time_utc
        self._current_monotonic_seconds: float = start_monotonic_seconds

    def now_utc(self) -> datetime:
        """Return the frozen UTC time."""
        return self._current_time_utc

    def today_utc(self) -> date:
        """Return the frozen UTC date."""
        return self._current_time_utc.date()

    def monotonic_seconds(self) -> float:
        """Return the frozen monotonic value."""
        return self._current_monotonic_seconds

    def advance(self, delta: timedelta) -> None:
        """
        Advance the clock by a duration.

        Args:
            delta: Time to advance (must be non-negative).

        Raises:
            ValueError: If delta is negative.
        """
        if delta.total_seconds() < 0:
            raise ValueError('delta must be non-negative.')

        self._current_time_utc += delta
        self._current_monotonic_seconds += delta.total_seconds()

    def set_time(self, new_time_utc: datetime) -> None:
        """
        Set the clock to a specific UTC time.

        Does not adjust the monotonic counter—use advance() for
        correlated wall/monotonic changes.

        Args:
            new_time_utc: New time (must be timezone-aware UTC).

        Raises:
            ValueError: If new_time_utc is naive or not UTC.
        """
        if new_time_utc.tzinfo is None:
            raise ValueError('new_time_utc must be timezone-aware (UTC).')
        if new_time_utc.tzinfo is not UTC:
            raise ValueError('new_time_utc must use datetime.UTC.')

        self._current_time_utc = new_time_utc


@dataclass(frozen=True, slots=True)
class OffsetClock:
    """
    Clock decorator applying a constant offset to another clock.

    Useful for replaying runs as if they occurred at a different time
    or simulating time travel in integration tests.

    Attributes:
        base_clock: The underlying clock to wrap.
        offset: Constant offset applied to wall time (not monotonic).

    Example:
        >>> base = SystemClock()
        >>> yesterday = OffsetClock(base_clock=base, offset=timedelta(days=-1))
        >>> yesterday.now_utc() < base.now_utc()
        True
    """

    base_clock: Clock
    offset: timedelta

    def now_utc(self) -> datetime:
        """Return base clock time plus offset."""
        return self.base_clock.now_utc() + self.offset

    def today_utc(self) -> date:
        """Return offset-adjusted date."""
        return self.now_utc().date()

    def monotonic_seconds(self) -> float:
        """Return base clock monotonic time (offset not applied)."""
        return self.base_clock.monotonic_seconds()


# =============================================================================
# Duration Measurement
# =============================================================================


@dataclass(frozen=True, slots=True)
class Stopwatch:
    """
    Elapsed-time measurement using monotonic time.

    Safer than wall-clock time for durations since monotonic time
    is unaffected by system clock adjustments.

    Attributes:
        start_monotonic_seconds: Monotonic timestamp when started.

    Example:
        >>> stopwatch = Stopwatch.start(clock=system_clock)
        >>> # ... work ...
        >>> elapsed = stopwatch.elapsed_seconds(clock=system_clock)

    Note:
        Use the same clock instance for start and elapsed measurement.
    """

    start_monotonic_seconds: float

    @classmethod
    def start(cls, *, clock: Clock) -> Self:
        """
        Create and start a stopwatch.

        Args:
            clock: Clock providing monotonic_seconds().

        Returns:
            A started Stopwatch instance.
        """
        return cls(start_monotonic_seconds=clock.monotonic_seconds())

    def elapsed_seconds(self, *, clock: Clock) -> float:
        """
        Compute elapsed seconds since start.

        Args:
            clock: Clock providing monotonic_seconds().

        Returns:
            Elapsed time in seconds.
        """
        return clock.monotonic_seconds() - self.start_monotonic_seconds


class Timer:
    """
    Context manager for timing code blocks.

    Captures both wall time (for logging context) and monotonic time
    (for accurate duration measurement).

    Attributes:
        label: Identifier for this timing operation.
        started_at_utc: Wall time when entered (for logs).
        elapsed_seconds: Duration in seconds (set on exit).

    Example:
        >>> with Timer(clock=clock, label='compute_z_scores') as timer:
        ...     compute_z_scores()
        >>> logger.info('%s completed in %.3fs', timer.label, timer.elapsed_seconds)
    """

    __slots__ = (
        '_clock',
        '_elapsed_seconds',
        '_label',
        '_started_at_utc',
        '_stopwatch',
    )

    def __init__(self, *, clock: Clock, label: str) -> None:
        """
        Initialize a timer.

        Args:
            clock: Clock for time measurement.
            label: Descriptive label for logging.

        Raises:
            ValueError: If label is empty or whitespace.
        """
        if not label.strip():
            raise ValueError('label must be a non-empty string.')

        self._clock: Clock = clock
        self._label: str = label
        self._started_at_utc: datetime | None = None
        self._stopwatch: Stopwatch | None = None
        self._elapsed_seconds: float | None = None

    @property
    def label(self) -> str:
        """Timer label for identification."""
        return self._label

    @property
    def started_at_utc(self) -> datetime | None:
        """Wall time when timer started, or None if not started."""
        return self._started_at_utc

    @property
    def elapsed_seconds(self) -> float | None:
        """Elapsed duration in seconds, or None if not completed."""
        return self._elapsed_seconds

    def __enter__(self) -> Self:
        """Start the timer."""
        self._started_at_utc = self._clock.now_utc()
        self._stopwatch = Stopwatch.start(clock=self._clock)

        logger.debug(
            'Timer started: label=%r at=%s',
            self._label,
            self._started_at_utc.isoformat(),
        )

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        """
        Stop the timer and record elapsed duration.

        Returns:
            False (exceptions are not suppressed).
        """
        if self._stopwatch is None:
            logger.error(
                'Timer.__exit__ called without __enter__: label=%r', self._label
            )
            return False

        self._elapsed_seconds = self._stopwatch.elapsed_seconds(clock=self._clock)

        logger.debug(
            'Timer completed: label=%r elapsed=%.6fs',
            self._label,
            self._elapsed_seconds,
        )

        return False
