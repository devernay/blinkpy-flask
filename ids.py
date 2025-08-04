"""ID validation classes for the Blink Camera Flask application."""

import re

from config import Config


class BaseId:
    """Base class for validated ID types.

    Provides common validation and comparison functionality for ID classes.
    Subclasses must implement _get_pattern() and _get_type_name().

    Attributes:
        value: The validated ID string value
    """

    def __init__(self, value: str | int | float) -> None:
        """Initialize and validate ID value.

        Args:
            value: String or numeric ID to validate

        Raises:
            ValueError: If value is empty or doesn't match pattern
        """
        # Convert to string if needed
        if isinstance(value, int | float):
            value = str(value)

        self.value = self._validate(value)

    def _validate(self, value: str) -> str:
        """Validate ID value against pattern.

        Args:
            value: String to validate

        Returns:
            Validated and stripped string

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, str):
            raise ValueError(f"{self._get_type_name()} must be a string")

        value = value.strip()
        if not value:
            raise ValueError(f"{self._get_type_name()} cannot be empty")

        # Use the specific pattern from the subclass
        pattern = self._get_pattern()
        if not re.match(pattern, value):
            raise ValueError(f"Invalid {self._get_type_name()} format")
        return value

    def _get_pattern(self) -> str:
        """Get validation regex pattern.

        Returns:
            Regex pattern string for validation

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_pattern")

    def _get_type_name(self) -> str:
        """Get human-readable type name.

        Returns:
            Type name for error messages

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_type_name")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Check equality with another BaseId instance."""
        return isinstance(other, self.__class__) and self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash(self.value)

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

    def _get_pattern(self) -> str:
        """Get camera ID validation pattern."""
        return Config.VALID_CAMERA_ID_PATTERN

    def _get_type_name(self) -> str:
        """Get type name for error messages."""
        return "Camera ID"


class NetworkId(BaseId):
    """Validated network identifier.

    Represents a unique Blink network/system ID with validation.
    Used for system-level operations like arming/disarming.
    """

    def _get_pattern(self) -> str:
        """Get network ID validation pattern."""
        return Config.VALID_NETWORK_ID_PATTERN

    def _get_type_name(self) -> str:
        """Get type name for error messages."""
        return "Network ID"


class ClipId(BaseId):
    """Validated clip identifier.

    Represents a unique clip ID for both cloud and local storage clips.
    Local clips use format 'sync_name~item_id', cloud clips use numeric IDs.
    """

    def _get_pattern(self) -> str:
        """Get clip ID validation pattern."""
        return Config.VALID_CLIP_ID_PATTERN

    def _get_type_name(self) -> str:
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

    def is_local(self) -> bool:
        """Check if this is a local storage clip.

        Returns:
            True if local storage clip, False if cloud clip
        """
        return "~" in self.value

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

    @classmethod
    def from_cloud(cls, clip_id: int | str) -> "ClipId":
        """Create ClipId for cloud storage clip.

        Args:
            clip_id: Numeric ID of the cloud clip

        Returns:
            ClipId instance for cloud clip
        """
        return cls(str(clip_id))
