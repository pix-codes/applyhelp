import base64
import logging
import urllib.parse
from email.message import EmailMessage

import httpx
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models import AppSetting
from app.repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"


class GmailClient:
    """
    Gmail Integration using Google's official REST API with minimal scope (gmail.compose).
    Does NOT request mailbox read access.
    Stores refresh tokens encrypted at rest.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.repo = SettingsRepository(db)

    @property
    def client_id(self) -> str | None:
        return self.repo.get("google_client_id") or self.settings.google_client_id

    @property
    def client_secret(self) -> str | None:
        return self.repo.get("google_client_secret") or self.settings.google_client_secret

    @property
    def redirect_uri(self) -> str:
        return self.repo.get("google_redirect_uri") or self.settings.google_redirect_uri

    def get_authorization_url(self) -> str:
        cid = self.client_id
        if not cid:
            raise ValueError("GOOGLE_CLIENT_ID is not configured (set via UI in Settings or .env)")

        params = {
            "client_id": cid,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = urllib.parse.urlencode(params)
        return f"{AUTH_URL}?{query}"

    async def exchange_code_for_tokens(self, auth_code: str) -> bool:
        cid = self.client_id
        csec = self.client_secret
        if not cid or not csec:
            raise ValueError("Google OAuth credentials missing")

        payload = {
            "code": auth_code,
            "client_id": cid,
            "client_secret": csec,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URL, data=payload)
            if resp.status_code != 200:
                logger.error("Failed to exchange auth code: %s", resp.text)
                return False

            tokens = resp.json()
            refresh_token = tokens.get("refresh_token")
            if refresh_token:
                self._save_token("gmail_refresh_token", refresh_token)
            return True

    def _save_token(self, key: str, token: str) -> None:
        enc_val = encrypt_secret(token)
        setting = self.db.get(AppSetting, key)
        if not setting:
            setting = AppSetting(key=key, value=enc_val, is_encrypted=True)
            self.db.add(setting)
        else:
            setting.value = enc_val
            setting.is_encrypted = True
        self.db.commit()

    def _get_token(self, key: str) -> str | None:
        setting = self.db.get(AppSetting, key)
        if setting and setting.value:
            return decrypt_secret(setting.value)
        return None

    def is_connected(self) -> bool:
        return self._get_token("gmail_refresh_token") is not None

    def revoke_connection(self) -> None:
        setting = self.db.get(AppSetting, "gmail_refresh_token")
        if setting:
            self.db.delete(setting)
            self.db.commit()

    async def _get_access_token(self) -> str | None:
        refresh_token = self._get_token("gmail_refresh_token")
        if not refresh_token:
            return None

        cid = self.client_id
        csec = self.client_secret
        if not cid or not csec:
            return None

        payload = {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URL, data=payload)
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.error("Failed to refresh Gmail access token: %s", resp.text)
            return None

    async def create_draft(self, subject: str, body: str, to_email: str | None = None) -> str | None:
        access_token = await self._get_access_token()
        if not access_token:
            raise RuntimeError("Gmail not connected or failed to acquire access token")

        msg = EmailMessage()
        msg["Subject"] = subject
        if to_email:
            msg["To"] = to_email
        msg.set_content(body)

        raw_bytes = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "message": {
                "raw": raw_bytes
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(DRAFTS_URL, headers=headers, json=payload)
            if resp.status_code in [200, 201]:
                draft_data = resp.json()
                draft_id = draft_data.get("id")
                logger.info("Successfully created Gmail draft with ID: %s", draft_id)
                return draft_id
            else:
                logger.error("Failed to create Gmail draft: %s", resp.text)
                raise RuntimeError(f"Gmail Draft Creation Failed: {resp.status_code} {resp.text}")
