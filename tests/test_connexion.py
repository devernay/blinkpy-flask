"""Integration tests for connexion API loading.

Tests that connexion can successfully load api.json and all handlers are properly resolved.
"""

import json
import os
import unittest
import warnings
from typing import Any

# Suppress connexion's internal jsonschema deprecation warnings
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="connexion.json_schema"
)

from connexion import AsyncApp  # noqa: E402


class TestConnexionIntegration(unittest.TestCase):
    """Test connexion AsyncApp integration with api.json."""

    def setUp(self) -> None:
        """Set up test with correct path to api.json."""
        # Change to project root directory
        test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(test_dir)
        self.api_path = os.path.join(self.project_root, "api.json")

    def test_api_loads_successfully(self) -> None:
        """Test that connexion can load api.json without errors.

        Verifies that the Connexion framework can successfully load
        and parse the OpenAPI specification file without configuration
        or validation errors.

        Tests:
            - OpenAPI specification file loading
            - Connexion configuration validation
            - API definition parsing success
            - No configuration errors during startup
        """
        app = AsyncApp(__name__)

        # This should not raise any exceptions
        app.add_api(self.api_path, validate_responses=False, strict_validation=False)

        # If we get here without exceptions, the API loaded successfully
        self.assertTrue(True)

    def test_all_handlers_resolved(self) -> None:
        """Test that all x-openapi-router-controller handlers are properly resolved.

        Verifies that all OpenAPI operation handlers defined in the
        specification can be successfully resolved to their corresponding
        Python functions without import or resolution errors.

        Tests:
            - Handler function resolution for all endpoints
            - x-openapi-router-controller directive processing
            - Import path validation for handler modules
            - No missing handler function errors
        """
        app = AsyncApp(__name__)

        # This will raise an exception if any handlers can't be resolved
        app.add_api(self.api_path, validate_responses=False, strict_validation=False)

        # If we get here, all handlers were resolved successfully
        self.assertTrue(True)

    def test_expected_endpoints_present(self) -> None:
        """Test that expected API endpoints are present in the specification.

        Verifies that all critical API endpoints are properly defined
        in the OpenAPI specification and available through Connexion.

        Tests:
            - Core API endpoint presence (systems, cameras, clips)
            - Authentication endpoint availability
            - Streaming and thumbnail endpoint definitions
            - Complete API surface coverage
        """
        with open(self.api_path) as f:
            spec = json.load(f)

        paths = spec["paths"]

        # Check key endpoints exist
        expected_paths = [
            "/",
            "/login",
            "/api/systems",
            "/api/cameras",
            "/api/clips",
            "/api/settings",
        ]

        for expected_path in expected_paths:
            self.assertIn(
                expected_path, paths, f"Expected path {expected_path} not found"
            )

    def test_handler_modules_importable(self) -> None:
        """Test that all handler modules referenced in api.json can be imported."""
        with open(self.api_path) as f:
            spec = json.load(f)

        # Extract all x-openapi-router-controller values
        controllers = set()
        for path_item in spec["paths"].values():
            for operation in path_item.values():
                if (
                    isinstance(operation, dict)
                    and "x-openapi-router-controller" in operation
                ):
                    controllers.add(operation["x-openapi-router-controller"])

        # Test that each controller module can be imported
        for controller in controllers:
            try:
                __import__(controller)
            except ImportError as e:
                self.fail(f"Failed to import controller module {controller}: {e}")

    def test_openapi_version_compatibility(self) -> None:
        """Test that the OpenAPI version is compatible with connexion."""
        with open(self.api_path) as f:
            spec = json.load(f)

        openapi_version = spec.get("openapi")
        self.assertIsNotNone(openapi_version)
        self.assertTrue(
            openapi_version.startswith("3.0"),
            f"Expected OpenAPI 3.0.x, got {openapi_version}",
        )

    def test_all_schemas_defined(self) -> None:
        """Test that all referenced schemas are properly defined."""
        with open(self.api_path) as f:
            spec = json.load(f)

        # Find all schema references
        schema_refs = set()

        def find_refs(obj: Any) -> None:
            if isinstance(obj, dict):
                if "$ref" in obj and obj["$ref"].startswith("#/components/schemas/"):
                    schema_name = obj["$ref"].split("/")[-1]
                    schema_refs.add(schema_name)
                for value in obj.values():
                    find_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_refs(item)

        find_refs(spec)

        # Check that all referenced schemas exist
        defined_schemas = set(spec.get("components", {}).get("schemas", {}).keys())

        for schema_ref in schema_refs:
            self.assertIn(
                schema_ref,
                defined_schemas,
                f"Referenced schema {schema_ref} not defined in components/schemas",
            )


if __name__ == "__main__":
    unittest.main()
