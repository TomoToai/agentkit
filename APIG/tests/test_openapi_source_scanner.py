import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_openapi_from_source import BUSINESS_OPERATIONS, build_spec, render_yaml, scan_routes  # noqa: E402


class OpenApiSourceScannerTest(unittest.TestCase):
    def test_scans_all_business_routes_from_source(self):
        self.assertTrue(set(BUSINESS_OPERATIONS).issubset(scan_routes(ROOT / "server.py")))

    def test_generates_openapi_for_business_scope_only(self):
        spec = build_spec(ROOT / "server.py", "https://example.invalid")
        self.assertEqual(set(spec["paths"]), {
            "/api/cameras",
            "/api/cameras/{camera_id}",
            "/api/cameras/{camera_id}/diagnostics",
            "/api/alerts",
            "/api/product-guides",
            "/api/product-guides/{sku}",
            "/api/cameras/{camera_id}/maintenance-status",
        })
        self.assertNotIn("/api/agent/chat", spec["paths"])
        self.assertEqual(spec["security"], [{"ApiKeyAuth": []}])
        self.assertEqual(spec["components"]["securitySchemes"]["ApiKeyAuth"]["name"], "X-API-Key")
        rendered = render_yaml(spec)
        self.assertIn("update_camera_maintenance_status", rendered)
        self.assertIn("list_product_guides", rendered)
        self.assertIn("get_product_guide", rendered)
        self.assertIn("X-API-Key", rendered)
        self.assertIn("ApiKeyAuth: []", rendered)
        self.assertIn('"200":', rendered)


if __name__ == "__main__":
    unittest.main()
