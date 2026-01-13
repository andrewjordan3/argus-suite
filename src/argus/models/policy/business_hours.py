# argus/models/policy/business_hours.py
"""
=============================================================================
BUSINESS HOURS CONFIGURATION
=============================================================================
Defines business hours for identifying transactions outside normal operations.
This can help detect personal use, unauthorized activity, or fraud.
"""

import logging
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__: list[str] = ['BusinessHoursConfig']

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class BusinessHoursConfig(BaseModel):
    """
    Configuration for business hours definition.

    Used to identify transactions that occur outside normal business operations,
    which may indicate personal use, unauthorized activity, or fraud.

    TIMEZONE HANDLING:
    ------------------
    All datetime processing in this application uses UTC internally.

    - **Timezone-aware input** (recommended):
      If input datetimes have timezone information, they will be converted to UTC.
      Example: "2024-12-15 14:00:00-06:00" (CST) → "2024-12-15 20:00:00+00:00" (UTC)

    - **Timezone-naive input** (not recommended):
      If input datetimes lack timezone information, they are treated as-is without conversion.
      Example: "2024-12-15 14:00:00" → "2024-12-15 14:00:00" (no conversion applied)

    **IMPORTANT**: Specify business hours to match your data's timezone convention.
    See config.yaml comments for detailed guidance.

    Attributes:
        start_hour: Hour when business day starts (0-23, 24-hour format).
        end_hour: Hour when business day ends (0-23, 24-hour format).
        days_of_week: List of business days (0=Monday, 6=Sunday).
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    start_hour: int = Field(
        default=6,
        description='Hour when business day starts (0-23, 24-hour format).',
        ge=0,
        le=23,
    )

    end_hour: int = Field(
        default=16,
        description='Hour when business day ends (0-23, 24-hour format).',
        ge=0,
        le=23,
    )

    days_of_week: tuple[int, ...] = Field(
        default=(0, 1, 2, 3, 4),
        description='Sequence of business days (0=Monday, 6=Sunday)',
        min_length=1,
        max_length=7,
    )

    @field_validator('days_of_week')
    @classmethod
    def validate_days_of_week(
        cls, days: list[int] | tuple[int, ...]
    ) -> tuple[int, ...]:
        """
        Validate that all day values are between 0 (Monday) and 6 (Sunday).

        Args:
            days: List of day numbers.

        Returns:
            Validated tuple of days, sorted for consistency.

        Raises:
            ValueError: If any day is not in range 0-6 or duplicates exist.
        """
        for day in days:
            if not (0 <= day <= 6):  # noqa: PLR2004
                raise ValueError(
                    f'Day of week must be between 0 (Monday) and 6 (Sunday), got {day}'
                )

        # Check for duplicates
        if len(days) != len(set(days)):
            raise ValueError('days_of_week contains duplicate values')

        return tuple(sorted(days))  # Return sorted for consistency

    @model_validator(mode='after')
    def validate_hour_ordering(self) -> Self:
        """
        Validate that start_hour and end_hour are not equal.

        Allows for overnight shifts if end_hour < start_hour, but logs a warning
        since this may indicate misconfiguration.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If start_hour equals end_hour.
        """
        if self.start_hour == self.end_hour:
            raise ValueError(
                f'start_hour and end_hour cannot be equal ({self.start_hour})'
            )

        # Note: We allow start_hour > end_hour for overnight shifts (e.g., 22-6)
        if self.start_hour > self.end_hour:
            logger.warning(
                'Business start time is LATER than end time. Please verify this is '
                'intentional.\nstart_hour=%d\tend_hour=%d',
                self.start_hour,
                self.end_hour,
            )

        return self

    def is_business_hours(self, hour: int, day_of_week: int) -> bool:
        """
        Check if a given hour and day of week falls within business hours.

        Handles overnight shifts (e.g., 22:00-06:00) correctly by checking
        if the hour is outside the non-business period.

        Args:
            hour: Hour to check (0-23).
            day_of_week: Day to check (0=Monday, 6=Sunday).

        Returns:
            True if within business hours, False otherwise.

        Example:
            >>> config = BusinessHoursConfig(
            ...     start_hour=6,
            ...     end_hour=16,
            ...     days_of_week=[0, 1, 2, 3, 4]
            ... )
            >>> config.is_business_hours(hour=10, day_of_week=2)  # Wed 10am
            True
            >>> config.is_business_hours(hour=18, day_of_week=2)  # Wed 6pm
            False
        """
        is_business_day: bool = day_of_week in self.days_of_week

        # Handle normal hours (start < end) and overnight shifts (start > end)
        if self.start_hour < self.end_hour:
            # Normal hours: 6am-4pm
            is_business_time: bool = self.start_hour <= hour < self.end_hour
        else:
            # Overnight shift: 10pm-6am (hour >= 22 OR hour < 6)
            is_business_time = hour >= self.start_hour or hour < self.end_hour

        return is_business_day and is_business_time

    def get_day_name(self, day_of_week: int) -> str:
        """
        Get the name of a day from its number.

        Args:
            day_of_week: Day number (0=Monday, 6=Sunday).

        Returns:
            Day name string.
        """
        day_names: dict[int, str] = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday',
        }
        return day_names.get(day_of_week, 'Unknown')

    def get_business_days_display(self) -> str:
        """
        Get a human-readable string of business days.

        Returns:
            Comma-separated list of business day names.

        Example:
            >>> config.get_business_days_display()
            'Monday, Tuesday, Wednesday, Thursday, Friday'
        """
        return ', '.join(self.get_day_name(day) for day in self.days_of_week)

    def get_hours_display(self) -> str:
        """
        Get a human-readable string of business hours.

        Returns:
            String showing business hours range.

        Example:
            >>> config.get_hours_display()
            '06:00-16:00'
            >>> config_overnight.get_hours_display()
            '22:00-06:00 (overnight)'
        """
        is_overnight: bool = self.start_hour > self.end_hour
        suffix: Literal[' (overnight)'] | Literal[''] = (
            ' (overnight)' if is_overnight else ''
        )

        return f'{self.start_hour:02d}:00-{self.end_hour:02d}:00{suffix}'
