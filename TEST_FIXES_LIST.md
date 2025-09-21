# Tests to Fix: get_* → ensure_* Patches

## Status Legend
- [ ] TODO - Not started
- [✓] DONE - Successfully fixed and passing
- [✗] BROKEN - Test was already broken before fixing
- [!] BREAKING - Fix caused test to break, reverted
- [N] NO_CHANGE - Test actually needs get_* (tests None return)

## Tests in test_app.py

### get_blink_instance patches
- [✓] test_api_systems_success - DONE: Removed redundant get_blink_instance patch
- [ ] test_get_systems_success
- [ ] test_get_systems_with_devices_success
- [ ] test_get_system_details_success
- [ ] test_get_system_details_not_found
- [ ] test_update_system_success
- [ ] test_get_cameras_success
- [ ] test_get_cameras_empty_list
- [ ] test_get_camera_details_success
- [ ] test_get_camera_details_not_found
- [ ] test_get_camera_details_invalid_id
- [ ] test_get_clips_cloud_success
- [ ] test_get_clips_local_success
- [ ] test_get_clips_invalid_storage
- [ ] test_get_camera_thumbnail_success
- [ ] test_get_camera_thumbnail_not_found
- [ ] test_get_camera_thumbnail_invalid_id
- [ ] test_get_camera_thumbnail_check_true
- [ ] test_get_camera_thumbnail_check_false
- [ ] test_delete_camera_thumbnail_success
- [ ] test_delete_camera_thumbnail_not_found
- [ ] test_delete_camera_thumbnail_invalid_id
- [ ] test_record_camera_success
- [ ] test_record_camera_not_found
- [ ] test_record_camera_invalid_id

### get_blink_connection patches
- [ ] test_start_camera_stream_success
- [ ] test_start_camera_stream_not_found
- [ ] test_start_camera_stream_invalid_id
- [ ] test_stop_camera_stream_success
- [ ] test_stop_camera_stream_not_found
- [ ] test_get_stream_segment_success
- [ ] test_get_stream_segment_not_found
- [ ] test_get_stream_segment_invalid_format
- [ ] test_get_stream_segment_file_not_found
- [ ] test_clear_all_cache_success
- [ ] test_clear_thumbnails_cache_success
- [ ] test_clear_clips_cache_success

## Tests in test_services.py

### get_blink_instance patches
- [ ] test_cleanup_blink_session_with_instance
- [ ] test_cleanup_blink_session_without_instance
- [ ] test_cleanup_blink_session_with_auth_error
- [ ] test_cleanup_blink_session_with_connection_error
- [ ] test_cleanup_blink_session_with_timeout_error
- [ ] test_get_blink_connection_success
- [ ] test_get_blink_connection_not_initialized
- [ ] test_get_blink_connection_initialization_error
- [ ] test_get_blink_connection_startup_error
- [ ] test_get_blink_connection_timeout_error
- [ ] test_get_blink_connection_with_existing_connection
- [ ] test_get_blink_connection_with_cleanup_error
- [ ] test_get_blink_connection_with_thread_error
- [ ] test_get_blink_connection_with_loop_error
- [ ] test_get_blink_connection_with_stream_cleanup_error
- [ ] test_get_blink_connection_with_multiple_errors
- [ ] test_get_blink_connection_with_partial_cleanup
- [ ] test_get_blink_connection_with_connection_reuse
- [ ] test_get_blink_connection_with_connection_recreation
- [ ] test_get_blink_connection_with_graceful_shutdown
- [ ] test_get_blink_connection_with_forced_shutdown
- [ ] test_get_blink_connection_with_stream_management
- [ ] test_get_blink_connection_with_concurrent_access
- [ ] test_get_blink_connection_with_resource_cleanup
- [ ] test_get_blink_connection_with_error_recovery

## Special Cases to Check
- Tests that specifically test None return values should keep get_* patches
- Tests that verify uninitialized state behavior should keep get_* patches
