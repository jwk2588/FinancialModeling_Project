import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "Nexus Canon API — DraftKings Beta"
    version: str = "0.3.0"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./nexus_dk.db")
    api_prefix: str = "/api"
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    corpus_dir: str = os.getenv("CORPUS_DIR", "./corpus")
    default_agent: str = "master_nexus"
    export_dir: str = os.getenv("EXPORT_DIR", "./exports")

settings = Settings()
