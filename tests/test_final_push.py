#!/usr/bin/env python3
"""Final push to reach 70% coverage - targeting easy wins."""

import unittest

from blinkapp.models.ids import CameraId, NetworkId


class TestFinalPush(unittest.TestCase):
    """Test simple functions to push coverage over 70%."""

    def test_camera_id_edge_cases(self):
        """Test CameraId edge cases."""
        # Test with string input
        camera_id = CameraId("12345")
        self.assertEqual(int(camera_id), 12345)

        # Test comparison
        camera_id2 = CameraId(12345)
        self.assertEqual(camera_id, camera_id2)

    def test_network_id_edge_cases(self):
        """Test NetworkId edge cases."""
        # Test with string input
        network_id = NetworkId("67890")
        self.assertEqual(int(network_id), 67890)

        # Test comparison
        network_id2 = NetworkId(67890)
        self.assertEqual(network_id, network_id2)

    def test_id_string_representations(self):
        """Test string representations of ID classes."""
        camera_id = CameraId(12345)
        self.assertIn("12345", str(camera_id))

        network_id = NetworkId(67890)
        self.assertIn("67890", str(network_id))

    def test_id_hash_functionality(self):
        """Test hash functionality for ID classes."""
        camera_id1 = CameraId(12345)
        camera_id2 = CameraId(12345)

        # Should be hashable and equal
        self.assertEqual(hash(camera_id1), hash(camera_id2))

        network_id1 = NetworkId(67890)
        network_id2 = NetworkId(67890)

        self.assertEqual(hash(network_id1), hash(network_id2))
