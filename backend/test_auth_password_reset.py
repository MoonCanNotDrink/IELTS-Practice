import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler  # type: ignore
from slowapi.errors import RateLimitExceeded  # type: ignore
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.limiter import limiter
from app.models import Base, PasswordResetToken, User
from app.routes import auth as auth_module
from app.routes.auth import router as auth_router
from app.services.auth_service import get_password_hash


class AuthPasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.original_jwt_secret = settings.JWT_SECRET
        self.original_invite_code = settings.INVITE_CODE
        self.original_debug = settings.DEBUG
        self.original_app_base_url = settings.APP_BASE_URL
        settings.JWT_SECRET = "test-secret"
        settings.INVITE_CODE = "invite-code"
        settings.DEBUG = True
        settings.APP_BASE_URL = "http://testserver"

        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db", dir=str(settings.data_dir))
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._run_async(self._create_tables())

        self._reset_rate_limit_storage()

        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.include_router(auth_router)
        app.dependency_overrides = {
            auth_module.get_db: self._override_get_db,
        }
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._run_async(self.engine.dispose())
        os.unlink(self.db_path)
        settings.JWT_SECRET = self.original_jwt_secret
        settings.INVITE_CODE = self.original_invite_code
        settings.DEBUG = self.original_debug
        settings.APP_BASE_URL = self.original_app_base_url
        self._reset_rate_limit_storage()

    def _run_async(self, coro):
        import asyncio

        return asyncio.run(coro)

    def _reset_rate_limit_storage(self):
        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "reset"):
            storage.reset()

    async def _create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db(self):
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _create_user(self, username: str, password: str, *, email: str | None = None) -> User:
        async with self.session_factory() as session:
            user = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
            )
            session.add(user)
            await session.flush()
            await session.commit()
            await session.refresh(user)
            return user

    async def _count_reset_tokens(self) -> int:
        async with self.session_factory() as session:
            result = await session.execute(select(func.count(PasswordResetToken.id)))
            return int(result.scalar_one())

    async def _get_user_by_username(self, username: str) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalars().first()

    def _login(self, username: str, password: str):
        return self.client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )

    def _extract_token_from_reset_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parse_qs(parsed.query)["token"][0]

    def test_register_accepts_email_and_returns_profile(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "Secret123",
                "invite_code": settings.INVITE_CODE,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("access_token", payload)

        profile_response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()["email"], "alice@example.com")

    def test_bind_email_updates_user_without_email(self):
        self._run_async(self._create_user("tester", "Secret123"))
        login_response = self._login("tester", "Secret123")
        self.assertEqual(login_response.status_code, 200)
        access_token = login_response.json()["access_token"]

        response = self.client.put(
            "/api/auth/email",
            json={"email": "tester@example.com"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "tester@example.com")

        user = self._run_async(self._get_user_by_username("tester"))
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "tester@example.com")

    def test_bind_email_rejects_duplicate_email(self):
        self._run_async(self._create_user("owner", "Secret123", email="owner@example.com"))
        self._run_async(self._create_user("tester", "Secret123"))
        login_response = self._login("tester", "Secret123")
        access_token = login_response.json()["access_token"]

        response = self.client.put(
            "/api/auth/email",
            json={"email": "owner@example.com"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Email already registered.")

    def test_password_reset_request_uses_generic_response(self):
        self._run_async(self._create_user("alice", "Secret123", email="alice@example.com"))

        with patch("app.routes.auth.send_password_reset_email") as send_email:
            existing_response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "alice@example.com"},
            )
            missing_response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "missing@example.com"},
            )

        self.assertEqual(existing_response.status_code, 200)
        self.assertEqual(missing_response.status_code, 200)
        self.assertEqual(existing_response.json(), missing_response.json())
        self.assertEqual(self._run_async(self._count_reset_tokens()), 1)
        send_email.assert_called_once()

    def test_password_reset_confirm_invalidates_old_access_and_refresh_tokens(self):
        self._run_async(self._create_user("alice", "Secret123", email="alice@example.com"))
        login_response = self._login("alice", "Secret123")
        self.assertEqual(login_response.status_code, 200)
        old_access = login_response.json()["access_token"]
        old_refresh = login_response.json()["refresh_token"]

        captured = {}

        def capture_reset_email(_email: str, reset_url: str):
            captured["reset_url"] = reset_url

        with patch("app.routes.auth.send_password_reset_email", side_effect=capture_reset_email):
            request_response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(request_response.status_code, 200)
        reset_token = self._extract_token_from_reset_url(captured["reset_url"])

        validate_response = self.client.post(
            "/api/auth/password-reset/validate",
            json={"token": reset_token},
        )
        self.assertEqual(validate_response.status_code, 200)

        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": "NewSecret123"},
        )
        self.assertEqual(confirm_response.status_code, 200)

        stale_access_response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        )
        self.assertEqual(stale_access_response.status_code, 401)

        stale_refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        self.assertEqual(stale_refresh_response.status_code, 401)

        relogin_response = self._login("alice", "NewSecret123")
        self.assertEqual(relogin_response.status_code, 200)

        second_validate_response = self.client.post(
            "/api/auth/password-reset/validate",
            json={"token": reset_token},
        )
        self.assertEqual(second_validate_response.status_code, 400)

    def test_second_password_reset_request_invalidates_previous_token(self):
        self._run_async(self._create_user("alice", "Secret123", email="alice@example.com"))

        captured_urls = []

        def capture_reset_email(_email: str, reset_url: str):
            captured_urls.append(reset_url)

        with patch("app.routes.auth.send_password_reset_email", side_effect=capture_reset_email):
            first_response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "alice@example.com"},
            )
            second_response = self.client.post(
                "/api/auth/password-reset/request",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(captured_urls), 2)

        first_token = self._extract_token_from_reset_url(captured_urls[0])
        second_token = self._extract_token_from_reset_url(captured_urls[1])

        first_validate = self.client.post(
            "/api/auth/password-reset/validate",
            json={"token": first_token},
        )
        second_validate = self.client.post(
            "/api/auth/password-reset/validate",
            json={"token": second_token},
        )

        self.assertEqual(first_validate.status_code, 400)
        self.assertEqual(second_validate.status_code, 200)


if __name__ == "__main__":
    unittest.main()
