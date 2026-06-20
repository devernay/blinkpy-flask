"""ID validation classes for the Blink Camera Flask application."""

import re
from collections.abc import Iterator

from blinkapp.config import Config

# Explicitly define what this module exports
__all__ = [
    "BaseId",
    "CameraId",
    "ClipId",
    "NetworkId",
]


class BaseId:
    """Base class for validated ID types using composition.

    Provides common validation and comparison functionality for ID classes.
    Subclasses must implement _get_pattern() and _get_type_name().

    Attributes:
        value: The validated ID string value
    """

    def __init__(self, value: str | float) -> None:
        """Initialize ID instance with validation.

        Args:
            value: String or numeric ID to validate

        Raises:
            ValueError: If value is empty or doesn't match pattern
        """
        # Convert to string if needed
        if isinstance(value, int | float):
            value = str(value)

        # Validate and store the value
        self.value = self._validate_static(value)

    @classmethod
    def _validate_static(cls, value: str) -> str:
        """Static validation method for use in __new__.

        Args:
            value: String to validate

        Returns:
            Validated string value

        Raises:
            ValueError: If validation fails
        """
        if not value or not value.strip():
            raise ValueError(f"{cls._get_type_name()} cannot be empty")

        cleaned_value = value.strip()
        pattern = cls._get_pattern()
        if pattern and not re.match(pattern, cleaned_value):
            raise ValueError(f"Invalid {cls._get_type_name()} format: {cleaned_value}")

        return cleaned_value

    def _validate(self, value: str) -> str:
        """Validate ID value against pattern.

        Args:
            value: String to validate

        Returns:
            Validated and stripped string

        Raises:
            ValueError: If validation fails
        """
        return self._validate_static(value)

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return f"{self.__class__.__name__}('{self.value}')"

    def __eq__(self, other: object) -> bool:
        """Check equality with another ID or string."""
        if isinstance(other, BaseId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash(self.value)

    def __len__(self) -> int:
        """Return length of the ID string."""
        return len(self.value)

    def __contains__(self, item: str) -> bool:
        """Check if substring is in the ID."""
        return item in self.value

    def __getitem__(self, key: int | slice) -> str:
        """Get character or slice from the ID."""
        return self.value[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over characters in the ID."""
        return iter(self.value)

    # String methods delegation (only methods actually used in the app)
    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
        """Split the ID string using the specified separator.

        Args:
            sep: The separator to use for splitting (default: None for whitespace).
            maxsplit: Maximum number of splits to perform (default: -1 for no limit).

        Returns:
            list[str]: List of string parts after splitting.
        """
        return self.value.split(sep, maxsplit)

    @classmethod
    def _get_pattern(cls) -> str:
        """Get validation regex pattern.

        Returns:
            Regex pattern string for validation

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_pattern")

    @classmethod
    def _get_type_name(cls) -> str:
        """Get human-readable type name.

        Returns:
            Type name for error messages

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_type_name")

    def __int__(self) -> int:
        """Convert to integer if possible."""
        try:
            return int(self.value)
        except ValueError as e:
            raise ValueError(
                f"Cannot convert {self._get_type_name()} '{self.value}' to integer"
            ) from e


# ID classes with validation
class CameraId(BaseId):
    """Validated camera identifier.

    Represents a unique camera ID with validation against the configured pattern.
    Used throughout the application to ensure type safety for camera operations.
    """

    @classmethod
    def _get_pattern(cls) -> str:
        """Get camera ID validation pattern."""
        return Config.VALID_CAMERA_ID_PATTERN

    @classmethod
    def _get_type_name(cls) -> str:
        """Get type name for error messages."""
        return "Camera ID"


class NetworkId(BaseId):
    """Validated network identifier.

    Represents a unique Blink network/system ID with validation.
    Used for system-level operations like arming/disarming.
    """

    @classmethod
    def _get_pattern(cls) -> str:
        """Get network ID validation pattern."""
        return Config.VALID_NETWORK_ID_PATTERN

    @classmethod
    def _get_type_name(cls) -> str:
        """Get type name for error messages."""
        return "Network ID"


class ClipId(BaseId):
    """Validated clip identifier.

    Represents a unique clip ID for both cloud and local storage clips.
    Local clips use format 'sync_name~item_id', cloud clips use numeric IDs.
    """

    @classmethod
    def _get_pattern(cls) -> str:
        """Get clip ID validation pattern."""
        return Config.VALID_CLIP_ID_PATTERN

    @classmethod
    def _get_type_name(cls) -> str:
        """Get type name for error messages."""
        return "Clip ID"

    @classmethod
    def from_local(cls, sync_name: str, item_id: int) -> "ClipId":
        """Create ClipId for local storage clip.

        Args:
            sync_name: Name of the sync module
            item_id: ID of the clip item

        Returns:
            ClipId instance for local clip
        """
        return cls(f"{sync_name}~{item_id}")

    LIVEVIEW_PREFIX = "liveview-"

    @classmethod
    def from_liveview(cls, camera_id: str, epoch: int) -> "ClipId":
        """Create ClipId for a server-side live-view recording.

        Args:
            camera_id: Camera the live view was recorded from
            epoch: Unix timestamp (microseconds) when the recording started

        Returns:
            ClipId instance of the form 'liveview-<camera_id>-<epoch>'
        """
        return cls(f"{cls.LIVEVIEW_PREFIX}{camera_id}-{epoch}")

    def is_local(self) -> bool:
        """Check if this is a local storage clip.

        Returns:
            True if local storage clip, False if cloud clip
        """
        return "~" in self.value

    def is_liveview(self) -> bool:
        """Check if this is a server-side live-view recording.

        Returns:
            True if this ID refers to a live-view recording.
        """
        return self.value.startswith(self.LIVEVIEW_PREFIX)

    def get_liveview_parts(self) -> tuple[str, int]:
        """Get camera id and start epoch for a live-view recording.

        Returns:
            Tuple of (camera_id, epoch_microseconds)

        Raises:
            ValueError: If this is not a live-view recording
        """
        if not self.is_liveview():
            raise ValueError("Not a live-view recording")
        rest = self.value[len(self.LIVEVIEW_PREFIX) :]
        camera_id, epoch_str = rest.rsplit("-", 1)
        return camera_id, int(epoch_str)

    def get_local_parts(self) -> tuple[str, int]:
        """Get sync name and item ID for local clips.

        Returns:
            Tuple of (sync_name, item_id)

        Raises:
            ValueError: If not a local clip
        """
        if not self.is_local():
            raise ValueError("Not a local storage clip")
        sync_name, item_id_str = self.value.split("~", 1)
        return sync_name, int(item_id_str)
