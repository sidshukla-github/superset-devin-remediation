from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    devin_api_key: str = ""
    devin_org_id: str = ""
    github_token: str = ""
    target_repo: str = "sidshukla-github/superset"
    webhook_secret: str = ""
    remediation_label: str = "devin-remediate"
    max_acu_limit: int = 15
    poll_interval_seconds: int = 20
    metrics_path: str = "/app/data/runs.jsonl"
    dry_run: bool = False
    http_ssl_verify: bool = True
    devin_ssl_verify: bool = True  # legacy alias; sets http_ssl_verify=false when false
    host: str = "0.0.0.0"
    port: int = 8080

    @model_validator(mode="after")
    def apply_legacy_ssl_flag(self) -> "Settings":
        if not self.devin_ssl_verify:
            self.http_ssl_verify = False
        return self

    @property
    def github_owner(self) -> str:
        return self.target_repo.split("/")[0]

    @property
    def github_repo(self) -> str:
        return self.target_repo.split("/")[1]

    @property
    def devin_configured(self) -> bool:
        return bool(self.devin_api_key and self.devin_org_id)

    @property
    def github_configured(self) -> bool:
        return bool(self.github_token)


settings = Settings()
