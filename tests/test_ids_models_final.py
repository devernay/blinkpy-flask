#!/usr/bin/env python3
"""Final targeted tests for models/ids.py - covering remaining missed lines."""

import unittest

from blinkapp.models.ids import CameraId, ClipId, NetworkId


class TestIdsModelsFinal(unittest.TestCase):
    """Test remaining uncovered ID model functions."""

    def test_camera_id_string_methods(self) -> None:
        """Test CameraId string method delegation."""
        camera_id = CameraId("test_camera_123")

        # Test split method
        parts = camera_id.split("_")
        self.assertEqual(parts, ["test", "camera", "123"])

        # Test contains
        self.assertTrue("camera" in camera_id)
        self.assertFalse("invalid" in camera_id)

        # Test getitem
        self.assertEqual(camera_id[0], "t")
        self.assertEqual(camera_id[5:11], "camera")

        # Test len
        self.assertEqual(len(camera_id), 15)

        # Test iter
        chars = list(camera_id)
        self.assertEqual(len(chars), 15)
        self.assertEqual(chars[0], "t")

    def test_clip_id_string_methods(self) -> None:
        """Test ClipId string method delegation."""
        clip_id = ClipId("clip_456")

        # Test split method
        parts = clip_id.split("_")
        self.assertEqual(parts, ["clip", "456"])

        # Test contains
        self.assertTrue("456" in clip_id)

        # Test getitem slice
        self.assertEqual(clip_id[:4], "clip")

    def test_network_id_string_methods(self) -> None:
        """Test NetworkId string method delegation."""
        network_id = NetworkId("789")

        # Test split method with maxsplit
        parts = network_id.split("8", 1)
        self.assertEqual(parts, ["7", "9"])

        # Test iteration
        first_char = next(iter(network_id))
        self.assertEqual(first_char, "7")

    def test_id_equality_with_string(self) -> None:
        """Test ID equality comparison with strings."""
        camera_id = CameraId("12345")

        # Test equality with string
        self.assertTrue(camera_id == "12345")
        self.assertFalse(camera_id == "54321")

        # Test equality with other types
        self.assertFalse(camera_id == 12345)
        self.assertFalse(camera_id is None)

    def test_id_hash_functionality(self) -> None:
        """Test ID hash functionality for sets and dicts."""
        camera_id1 = CameraId("test")
        camera_id2 = CameraId("test")
        camera_id3 = CameraId("different")

        # Test hash consistency
        self.assertEqual(hash(camera_id1), hash(camera_id2))
        self.assertNotEqual(hash(camera_id1), hash(camera_id3))

        # Test in sets
        id_set = {camera_id1, camera_id2, camera_id3}
        self.assertEqual(len(id_set), 2)  # camera_id1 and camera_id2 are equal
