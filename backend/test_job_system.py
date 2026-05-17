"""
Smoke tests for Mockup Studio V2 job APIs.

Run with:
    python -X utf8 test_job_system.py
"""

import io
import os
import sys
import time
import unittest

import cv2
import numpy as np
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.dirname(__file__)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.chdir(ROOT_DIR)

from main import app


def make_png(width=120, height=160, color=(40, 90, 220)):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = color
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not create test PNG")
    return buffer.tobytes()


class JobSystemTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def wait_for_job(self, job_id, timeout=20):
        deadline = time.time() + timeout
        last_payload = None
        while time.time() < deadline:
            response = self.client.get(f"/api/jobs/{job_id}")
            response.raise_for_status()
            payload = response.json()
            last_payload = payload
            if payload["status"] in {"completed", "completed_with_errors", "failed", "canceled"}:
                return payload
            time.sleep(0.2)
        self.fail(f"Job did not finish. Last payload: {last_payload}")

    def test_mockup_batch_job_finishes_with_outputs(self):
        mockups = self.client.get("/mockups").json()
        self.assertGreater(len(mockups), 0, "Need at least one mockup template")

        files = [
            ("designs", ("job-test-01.png", io.BytesIO(make_png()), "image/png")),
            ("designs", ("job-test-02.png", io.BytesIO(make_png(color=(220, 90, 40))), "image/png")),
        ]
        response = self.client.post(
            "/api/jobs/mockup-batch",
            data={
                "mockup_id": mockups[0]["id"],
                "naming_template": "{poster_name}_{mockup_name}_{index}",
                "target_kb": "120",
            },
            files=files,
        )
        response.raise_for_status()
        job_id = response.json()["job_id"]

        payload = self.wait_for_job(job_id)
        self.assertIn(payload["status"], {"completed", "completed_with_errors"})
        self.assertEqual(payload["percent"], 100)
        self.assertEqual(payload["completed"], 2)
        self.assertTrue(all(item["output_url"] for item in payload["items"]))

        zip_response = self.client.get(f"/api/exports/{job_id}/download")
        self.assertEqual(zip_response.status_code, 200)
        self.assertGreater(len(zip_response.content), 100)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
