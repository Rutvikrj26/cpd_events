"""
Google Cloud Storage service for file management.

Provides unified interface for uploading, downloading, and managing files in GCS.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class GCSStorage:
    """
    Google Cloud Storage service.

    Usage:
        from common.storage import gcs_storage

        # Upload file
        url = gcs_storage.upload(
            content=pdf_bytes,
            path='certificates/abc123.pdf',
            content_type='application/pdf'
        )

        # Get signed URL for private access
        signed_url = gcs_storage.get_signed_url('certificates/abc123.pdf')

        # Delete file
        gcs_storage.delete('certificates/abc123.pdf')
    """

    def __init__(self):
        self._client = None
        self._bucket = None

    @property
    def client(self):
        """Lazy-load GCS client."""
        if self._client is None:
            try:
                from google.cloud import storage

                self._client = storage.Client(project=settings.GCP_PROJECT_ID)
            except ImportError:
                logger.error("google-cloud-storage not installed")
                raise
        return self._client

    @property
    def bucket(self):
        """Get configured bucket."""
        if self._bucket is None:
            bucket_name = getattr(settings, 'GCS_BUCKET_NAME', None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME not configured in settings")
            self._bucket = self.client.bucket(bucket_name)
        return self._bucket

    @property
    def is_configured(self) -> bool:
        """Check if GCS is properly configured."""
        return bool(getattr(settings, 'GCS_BUCKET_NAME', None))

    def upload(
        self,
        content: bytes,
        path: str,
        content_type: str = 'application/octet-stream',
        public: bool = False,
        metadata: dict | None = None,
    ) -> str | None:
        """
        Upload content to GCS.

        Args:
            content: File content as bytes
            path: Destination path in bucket (e.g., 'certificates/abc.pdf')
            content_type: MIME type of the content
            public: If True, make file publicly accessible
            metadata: Optional custom metadata dict

        Returns:
            Public URL if public=True, otherwise gs:// URI
        """
        if not self.is_configured:
            logger.warning("GCS not configured, falling back to local storage")
            return self._save_local(content, path)

        try:
            blob = self.bucket.blob(path)

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload
            blob.upload_from_string(content, content_type=content_type)

            # Make public if requested
            if public:
                blob.make_public()
                return blob.public_url

            # Return gs:// URI for private files
            return f"gs://{self.bucket.name}/{path}"

        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return None

    def upload_file(
        self, file_path: str, destination_path: str, content_type: str = 'application/octet-stream', public: bool = False
    ) -> str | None:
        """
        Upload a local file to GCS.

        Args:
            file_path: Local file path
            destination_path: Destination path in bucket
            content_type: MIME type
            public: If True, make publicly accessible

        Returns:
            URL or gs:// URI
        """
        if not self.is_configured:
            return None

        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(file_path, content_type=content_type)

            if public:
                blob.make_public()
                return blob.public_url

            return f"gs://{self.bucket.name}/{destination_path}"

        except Exception as e:
            logger.error(f"GCS file upload failed: {e}")
            return None

    def download(self, path: str) -> bytes | None:
        """
        Download file content from GCS.

        Args:
            path: Path in bucket

        Returns:
            File content as bytes or None
        """
        if not self.is_configured:
            return None

        try:
            blob = self.bucket.blob(path)
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return None

    def delete(self, path: str) -> bool:
        """
        Delete a file from GCS.

        Args:
            path: Path in bucket

        Returns:
            True if deleted successfully
        """
        if not self.is_configured:
            return False

        try:
            blob = self.bucket.blob(path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"GCS delete failed: {e}")
            return False

    def exists(self, path: str) -> bool:
        """Check if file exists in GCS."""
        if not self.is_configured:
            return False

        try:
            blob = self.bucket.blob(path)
            return blob.exists()
        except Exception as e:
            logger.error(f"GCS exists check failed: {e}")
            return False

    def get_signed_url(self, path: str, expiration_minutes: int = 60, method: str = 'GET') -> str | None:
        """
        Generate a signed URL for temporary access.

        Args:
            path: Path in bucket
            expiration_minutes: URL expiration time
            method: HTTP method (GET for download, PUT for upload)

        Returns:
            Signed URL or None
        """
        if not self.is_configured:
            return None

        try:
            from datetime import timedelta

            blob = self.bucket.blob(path)
            url = blob.generate_signed_url(version='v4', expiration=timedelta(minutes=expiration_minutes), method=method)
            return url
        except Exception as e:
            logger.error(f"GCS signed URL generation failed: {e}")
            return None

    def get_public_url(self, path: str) -> str:
        """
        Get public URL for a file.

        Note: File must be publicly accessible.
        """
        bucket_name = getattr(settings, 'GCS_BUCKET_NAME', 'bucket')
        return f"https://storage.googleapis.com/{bucket_name}/{path}"

    def _save_local(self, content: bytes, path: str) -> str | None:
        """Fallback: save to local filesystem."""
        import os

        media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
        full_path = os.path.join(media_root, path)

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)

            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            return f"{media_url}{path}"
        except Exception as e:
            logger.error(f"Local save failed: {e}")
            return None


# Singleton instance
gcs_storage = GCSStorage()
