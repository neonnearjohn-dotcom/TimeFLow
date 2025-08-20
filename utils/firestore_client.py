import os
from typing import Optional

from google.cloud import firestore
from google.oauth2 import service_account

from utils.logging import get_logger

logger = get_logger(__name__)


def create_firestore_client() -> Optional[firestore.Client]:
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        if creds_path:
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            return firestore.Client(credentials=credentials, project=credentials.project_id)
        return firestore.Client()
    except Exception as e:
        logger.error("Firestore init failed", extra={"error": str(e)})
        return None
