"""Cloud storage providers and management."""
import boto3
from google.cloud import storage as gcs
import azure.storage.blob as azure_blob
from typing import Optional, Dict, Any, List, BinaryIO, Union
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
import mimetypes
import hashlib
import json
from datetime import datetime, timedelta
import asyncio
import aiofiles


class StorageProvider(Enum):
    """Supported cloud storage providers."""
    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_BLOB = "azure_blob"
    DROPBOX = "dropbox"
    LOCAL = "local"


@dataclass
class CloudFile:
    """Cloud file metadata."""
    name: str
    path: str
    size: int
    content_type: str
    etag: str
    last_modified: datetime
    provider: StorageProvider
    metadata: Dict[str, Any] = None


@dataclass
class UploadResult:
    """File upload result."""
    success: bool
    file_path: str
    size: int
    etag: Optional[str] = None
    error: Optional[str] = None


class BaseStorageProvider:
    """Base class for cloud storage providers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize storage provider.

        Args:
            config: Provider configuration
        """
        self.config = config

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload file to cloud storage.

        Args:
            local_path: Local file path
            remote_path: Remote file path
            content_type: MIME content type
            metadata: File metadata

        Returns:
            Upload result
        """
        raise NotImplementedError

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path]
    ) -> bool:
        """Download file from cloud storage.

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if successful
        """
        raise NotImplementedError

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from cloud storage.

        Args:
            remote_path: Remote file path

        Returns:
            True if successful
        """
        raise NotImplementedError

    def list_files(
        self,
        prefix: str = "",
        limit: Optional[int] = None
    ) -> List[CloudFile]:
        """List files in cloud storage.

        Args:
            prefix: Path prefix filter
            limit: Maximum number of files

        Returns:
            List of cloud files
        """
        raise NotImplementedError

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in cloud storage.

        Args:
            remote_path: Remote file path

        Returns:
            True if file exists
        """
        raise NotImplementedError

    def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get file information.

        Args:
            remote_path: Remote file path

        Returns:
            CloudFile object or None if not found
        """
        raise NotImplementedError

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> Optional[str]:
        """Generate signed URL for file access.

        Args:
            remote_path: Remote file path
            expiration: URL expiration time
            method: HTTP method

        Returns:
            Signed URL or None if not supported
        """
        raise NotImplementedError


class S3StorageProvider(BaseStorageProvider):
    """AWS S3 storage provider."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize S3 provider.

        Args:
            config: S3 configuration with bucket, region, credentials
        """
        super().__init__(config)
        self.bucket_name = config['bucket']
        self.client = boto3.client(
            's3',
            region_name=config.get('region', 'us-east-1'),
            aws_access_key_id=config.get('access_key_id'),
            aws_secret_access_key=config.get('secret_access_key')
        )

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload file to S3."""
        try:
            local_path = Path(local_path)

            # Detect content type
            if not content_type:
                content_type, _ = mimetypes.guess_type(str(local_path))
                content_type = content_type or 'application/octet-stream'

            # Prepare upload args
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata or {}
            }

            # Upload file
            self.client.upload_file(
                str(local_path),
                self.bucket_name,
                remote_path,
                ExtraArgs=extra_args
            )

            # Get file info
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )

            return UploadResult(
                success=True,
                file_path=remote_path,
                size=response['ContentLength'],
                etag=response['ETag'].strip('"')
            )

        except Exception as e:
            return UploadResult(
                success=False,
                file_path=remote_path,
                size=0,
                error=str(e)
            )

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path]
    ) -> bool:
        """Download file from S3."""
        try:
            self.client.download_file(
                self.bucket_name,
                remote_path,
                str(local_path)
            )
            return True
        except Exception:
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from S3."""
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            return True
        except Exception:
            return False

    def list_files(
        self,
        prefix: str = "",
        limit: Optional[int] = None
    ) -> List[CloudFile]:
        """List files in S3."""
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'Prefix': prefix
            }
            if limit:
                kwargs['MaxKeys'] = limit

            response = self.client.list_objects_v2(**kwargs)
            files = []

            for obj in response.get('Contents', []):
                files.append(CloudFile(
                    name=Path(obj['Key']).name,
                    path=obj['Key'],
                    size=obj['Size'],
                    content_type='application/octet-stream',  # S3 doesn't return content type in list
                    etag=obj['ETag'].strip('"'),
                    last_modified=obj['LastModified'],
                    provider=StorageProvider.AWS_S3
                ))

            return files

        except Exception:
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            return True
        except Exception:
            return False

    def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get S3 file information."""
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )

            return CloudFile(
                name=Path(remote_path).name,
                path=remote_path,
                size=response['ContentLength'],
                content_type=response.get('ContentType', 'application/octet-stream'),
                etag=response['ETag'].strip('"'),
                last_modified=response['LastModified'],
                provider=StorageProvider.AWS_S3,
                metadata=response.get('Metadata', {})
            )

        except Exception:
            return None

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> Optional[str]:
        """Generate signed URL for S3 file."""
        try:
            url = self.client.generate_presigned_url(
                'get_object' if method == 'GET' else 'put_object',
                Params={'Bucket': self.bucket_name, 'Key': remote_path},
                ExpiresIn=int(expiration.total_seconds())
            )
            return url
        except Exception:
            return None


class GoogleCloudStorageProvider(BaseStorageProvider):
    """Google Cloud Storage provider."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize GCS provider.

        Args:
            config: GCS configuration with bucket, credentials
        """
        super().__init__(config)
        self.bucket_name = config['bucket']
        self.client = gcs.Client.from_service_account_json(
            config.get('credentials_file')
        ) if config.get('credentials_file') else gcs.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload file to GCS."""
        try:
            local_path = Path(local_path)

            # Create blob
            blob = self.bucket.blob(remote_path)

            # Set metadata
            if metadata:
                blob.metadata = metadata

            # Set content type
            if content_type:
                blob.content_type = content_type
            else:
                content_type, _ = mimetypes.guess_type(str(local_path))
                blob.content_type = content_type or 'application/octet-stream'

            # Upload file
            blob.upload_from_filename(str(local_path))

            return UploadResult(
                success=True,
                file_path=remote_path,
                size=blob.size,
                etag=blob.etag
            )

        except Exception as e:
            return UploadResult(
                success=False,
                file_path=remote_path,
                size=0,
                error=str(e)
            )

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path]
    ) -> bool:
        """Download file from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(str(local_path))
            return True
        except Exception:
            return False

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception:
            return False

    def list_files(
        self,
        prefix: str = "",
        limit: Optional[int] = None
    ) -> List[CloudFile]:
        """List files in GCS."""
        try:
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                max_results=limit
            )

            files = []
            for blob in blobs:
                files.append(CloudFile(
                    name=Path(blob.name).name,
                    path=blob.name,
                    size=blob.size,
                    content_type=blob.content_type or 'application/octet-stream',
                    etag=blob.etag,
                    last_modified=blob.time_created,
                    provider=StorageProvider.GOOGLE_CLOUD,
                    metadata=blob.metadata
                ))

            return files

        except Exception:
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False

    def get_file_info(self, remote_path: str) -> Optional[CloudFile]:
        """Get GCS file information."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.reload()

            return CloudFile(
                name=Path(remote_path).name,
                path=remote_path,
                size=blob.size,
                content_type=blob.content_type or 'application/octet-stream',
                etag=blob.etag,
                last_modified=blob.time_created,
                provider=StorageProvider.GOOGLE_CLOUD,
                metadata=blob.metadata
            )

        except Exception:
            return None

    def generate_signed_url(
        self,
        remote_path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> Optional[str]:
        """Generate signed URL for GCS file."""
        try:
            blob = self.bucket.blob(remote_path)
            url = blob.generate_signed_url(
                expiration=datetime.utcnow() + expiration,
                method=method
            )
            return url
        except Exception:
            return None


class CloudStorageManager:
    """Manage multiple cloud storage providers."""

    def __init__(self):
        """Initialize cloud storage manager."""
        self.providers: Dict[str, BaseStorageProvider] = {}
        self.default_provider: Optional[str] = None

    def add_provider(
        self,
        name: str,
        provider_type: StorageProvider,
        config: Dict[str, Any],
        set_default: bool = False
    ) -> bool:
        """Add a storage provider.

        Args:
            name: Provider name
            provider_type: Type of provider
            config: Provider configuration
            set_default: Set as default provider

        Returns:
            True if added successfully
        """
        try:
            if provider_type == StorageProvider.AWS_S3:
                provider = S3StorageProvider(config)
            elif provider_type == StorageProvider.GOOGLE_CLOUD:
                provider = GoogleCloudStorageProvider(config)
            # elif provider_type == StorageProvider.AZURE_BLOB:
            #     provider = AzureBlobStorageProvider(config)
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")

            self.providers[name] = provider

            if set_default or not self.default_provider:
                self.default_provider = name

            return True

        except Exception as e:
            print(f"Error adding provider '{name}': {e}")
            return False

    def remove_provider(self, name: str) -> bool:
        """Remove a storage provider.

        Args:
            name: Provider name

        Returns:
            True if removed successfully
        """
        if name not in self.providers:
            return False

        del self.providers[name]

        if self.default_provider == name:
            self.default_provider = next(iter(self.providers), None)

        return True

    def get_provider(self, name: Optional[str] = None) -> Optional[BaseStorageProvider]:
        """Get storage provider.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Storage provider or None
        """
        if name is None:
            name = self.default_provider

        return self.providers.get(name) if name else None

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> UploadResult:
        """Upload file using specified or default provider.

        Args:
            local_path: Local file path
            remote_path: Remote file path
            provider: Provider name
            **kwargs: Additional upload options

        Returns:
            Upload result
        """
        storage_provider = self.get_provider(provider)
        if not storage_provider:
            return UploadResult(
                success=False,
                file_path=remote_path,
                size=0,
                error="No storage provider available"
            )

        return storage_provider.upload_file(local_path, remote_path, **kwargs)

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        provider: Optional[str] = None
    ) -> bool:
        """Download file using specified or default provider.

        Args:
            remote_path: Remote file path
            local_path: Local file path
            provider: Provider name

        Returns:
            True if successful
        """
        storage_provider = self.get_provider(provider)
        if not storage_provider:
            return False

        return storage_provider.download_file(remote_path, local_path)

    def sync_to_cloud(
        self,
        local_dir: Path,
        remote_prefix: str = "",
        provider: Optional[str] = None,
        delete_remote: bool = False
    ) -> Dict[str, UploadResult]:
        """Sync local directory to cloud storage.

        Args:
            local_dir: Local directory to sync
            remote_prefix: Remote path prefix
            provider: Provider name
            delete_remote: Delete remote files not in local

        Returns:
            Dictionary of file paths to upload results
        """
        storage_provider = self.get_provider(provider)
        if not storage_provider:
            return {}

        results = {}
        local_dir = Path(local_dir)

        # Upload local files
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                remote_path = f"{remote_prefix}/{relative_path}".replace('\\', '/')

                result = storage_provider.upload_file(file_path, remote_path)
                results[str(relative_path)] = result

        return results

    def list_providers(self) -> List[str]:
        """List available provider names.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())