import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

from app.routes.scoring import router as scoring_router


async def _fake_tts_response(req):
    return Response(content=b"fake-audio", media_type="audio/wav")


class TTSRouteTests(unittest.TestCase):
    def test_tts_rejects_anonymous_requests(self):
        app = FastAPI()
        app.include_router(scoring_router)

        with patch("app.routes.scoring._generate_tts_response", _fake_tts_response):
            with TestClient(app) as client:
                response = client.post("/api/scoring/tts", json={"text": "hello"})

        # Should require authentication
        self.assertEqual(response.status_code, 401)

    def test_tts_allows_authenticated_requests(self):
        app = FastAPI()
        app.include_router(scoring_router)

        # Override dependency to provide a fake user. Use the actual callable
        # object imported by the router so FastAPI applies the override.
        from app.routes import scoring as scoring_module

        class FakeUser:
            id = 1
            username = "tester"

        app.dependency_overrides = {
            scoring_module.get_current_user: lambda: FakeUser()
        }

        with patch("app.routes.scoring._generate_tts_response", _fake_tts_response):
            with TestClient(app) as client:
                # Provide a dummy Authorization header to satisfy OAuth2 scheme
                response = client.post(
                    "/api/scoring/tts",
                    json={"text": "hello"},
                    headers={"Authorization": "Bearer faketoken"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content, b"fake-audio")


if __name__ == "__main__":
    unittest.main()
