"""System management routes for the Blink Flask application."""

from flask import request

from blinkapp.models.ids import NetworkId
from blinkapp.utils.decorators import requires_blink
from blinkapp.utils.errors import ValidationError
from blinkapp.utils.validators import JsonDict
from config import Config
from route_decorators import (
    api_route,
    api_route_with_validation,
    simple_success_response,
)


def setup_system_routes(app):
    """Set up system management routes."""

    @app.route("/api/system/list")
    @requires_blink
    @api_route("get systems")
    def get_systems() -> JsonDict:
        """Get list of available Blink systems.

        Retrieves all configured Blink sync modules and their associated
        network information. Each system represents a separate Blink hub
        with its own set of cameras.

        Returns:
            JSON response with list of systems or error message
        """
        from blinkapp import blink, logger

        assert blink is not None  # Guaranteed by @requires_blink decorator

        logger.debug(f"Getting systems - sync count: {len(blink.sync)}")
        systems = []
        for name, sync in blink.sync.items():
            logger.debug(f"Processing sync: {name}, network_id: {sync.network_id}")
            systems.append(
                {
                    "name": name,
                    "network_id": sync.network_id,
                    "armed": sync.arm,
                    "online": sync.online,
                }
            )

        return {"systems": systems}

    @app.route("/api/system/<network_id_str>/devices")
    @requires_blink
    @api_route_with_validation(
        "get devices", validate_params={"network_id_str": NetworkId}
    )
    def get_devices(network_id: NetworkId) -> JsonDict:
        """Get devices for a specific Blink system.

        Args:
            network_id: Validated NetworkId object

        Returns:
            JSON response with list of devices or error message
        """
        from blinkapp import (
            create_device_data,
            ensure_thumbnail_cache_initialized,
            extract_thumbnail_timestamp,
            logger,
            require_sync_module,
            update_camera_thumbnail,
        )
        from blinkapp.models.ids import CameraId

        devices = []

        # Find the sync module for this network
        sync_module, error_response = require_sync_module(network_id)
        if error_response is not None:
            error_dict, status_code = error_response
            error_message = error_dict.get("error", "Unknown error")
            raise ValidationError(str(error_message), status_code)

        assert sync_module is not None
        # Add sync module
        devices.append(
            {
                "type": "sync_module",
                "name": "Sync Module",
                "online": sync_module.online,
                "id": sync_module.sync_id,
            }
        )

        # Add cameras - refresh thumbnails in Blink thread
        thumbnail_cache_instance = ensure_thumbnail_cache_initialized()
        for camera_name, camera in sync_module.cameras.items():
            logger.debug(
                f"Processing camera: {camera.name}, current thumbnail: {camera.thumbnail}"
            )

            cache_key = CameraId(camera.camera_id)
            current_ts = extract_thumbnail_timestamp(camera.thumbnail)
            cached_entry = thumbnail_cache_instance.get(cache_key)
            cached_ts = cached_entry.get("timestamp", 0) if cached_entry else 0

            # Update thumbnail if needed
            update_camera_thumbnail(camera, cache_key, current_ts, cached_ts)

            # Create device data
            device_data = create_device_data(camera, cache_key, current_ts, cached_ts)
            logger.debug(f"Camera device data for {camera.name}: {device_data}")
            devices.append(device_data)

        return {"devices": devices}

    @app.route("/api/system/<network_id_str>/arm", methods=["POST"])
    @requires_blink
    @api_route_with_validation(
        "arm/disarm system",
        validate_params={"network_id_str": NetworkId},
        validate_json=True,
        required_fields=["armed"],
    )
    def arm_system(network_id: NetworkId) -> JsonDict:
        """Arm or disarm a Blink system.

        Args:
            network_id: Validated NetworkId object

        Returns:
            JSON response with success status or error message
        """
        from blinkapp import blink_connection, error_context, require_sync_module

        data = request.get_json()
        armed = data["armed"]

        # Find the sync module
        sync_module, error_response = require_sync_module(network_id)
        if error_response is not None:
            error_dict, status_code = error_response
            error_message = error_dict.get("error", "Unknown error")
            raise ValidationError(str(error_message), status_code)

        with error_context("arm/disarm system"):
            if sync_module is not None:
                blink_connection.execute(sync_module.async_arm(armed))
            return {"armed": armed}

    @app.route("/api/system/refresh", methods=["POST"])
    @requires_blink
    @simple_success_response("System refreshed successfully")
    def refresh_system() -> JsonDict:
        """Manually refresh the Blink system.

        Returns:
            JSON response with success status or error message
        """
        from blinkapp import blink, blink_connection, create_api_response

        assert blink is not None
        success = blink_connection.execute(blink.refresh(force=True))

        if success is not True:
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
                status_code=500,
            )
            return response  # Return just the dict, not the tuple

        return {}  # Decorator will handle the success response
