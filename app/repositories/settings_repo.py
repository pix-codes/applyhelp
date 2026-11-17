from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret
from app.models import AppSetting


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = self.db.get(AppSetting, key)
        if not setting or setting.value is None:
            return default
        if setting.is_encrypted:
            val = decrypt_secret(setting.value)
            return val if val is not None else default
        return setting.value

    def set(self, key: str, value: Optional[str], encrypt: bool = True) -> None:
        setting = self.db.get(AppSetting, key)
        if value is None or value.strip() == "":
            if setting:
                self.db.delete(setting)
                self.db.commit()
            return

        stored_value = encrypt_secret(value.strip()) if encrypt else value.strip()

        if not setting:
            setting = AppSetting(key=key, value=stored_value, is_encrypted=encrypt)
            self.db.add(setting)
        else:
            setting.value = stored_value
            setting.is_encrypted = encrypt

        self.db.commit()

    def delete(self, key: str) -> None:
        setting = self.db.get(AppSetting, key)
        if setting:
            self.db.delete(setting)
            self.db.commit()
