"""Unit tests for upload validation and storage helpers (no network)."""

import pytest

from app.services.storage import (
    StorageNotConfigured,
    SupabaseStorage,
    UploadRejected,
    storage_key,
    validate_upload,
)


def test_validate_jpeg_ok():
    assert validate_upload("photo.jpg", "image/jpeg", 1024, 5, 40) == "image"


def test_validate_mp4_ok():
    assert validate_upload("clip.mp4", "video/mp4", 1024, 5, 40) == "video"


def test_validate_rejects_exe():
    with pytest.raises(UploadRejected):
        validate_upload("evil.exe", "application/x-msdownload", 1024, 5, 40)


def test_validate_rejects_empty():
    with pytest.raises(UploadRejected):
        validate_upload("photo.jpg", "image/jpeg", 0, 5, 40)


def test_validate_rejects_oversize_image():
    with pytest.raises(UploadRejected) as exc:
        validate_upload("big.jpg", "image/jpeg", 6 * 1024 * 1024, 5, 40)
    assert exc.value.code == "FILE_TOO_LARGE"


def test_validate_rejects_extension_mismatch():
    with pytest.raises(UploadRejected):
        validate_upload("photo.png", "image/jpeg", 1024, 5, 40)


def test_storage_key_has_no_user_input():
    key = storage_key("collection-items", 7, "image/png")
    assert key.startswith("uploads/collection-items/7/")
    assert key.endswith(".png")
    assert ".." not in key and " " not in key


def test_public_url_shape():
    store = SupabaseStorage("https://xyz.supabase.co", "key", "museum-media")
    assert store.public_url("uploads/a/b/c.jpg") == (
        "https://xyz.supabase.co/storage/v1/object/public/museum-media/uploads/a/b/c.jpg"
    )


def test_storage_requires_credentials():
    with pytest.raises(StorageNotConfigured):
        SupabaseStorage("", "", "museum-media")


def test_local_roundtrip(tmp_path):
    import anyio

    from app.services.storage import LocalStorage

    store = LocalStorage(str(tmp_path))
    url = anyio.run(store.upload, "uploads/events/1/a.jpg", b"bytes", "image/jpeg")
    assert url == "/uploads/uploads/events/1/a.jpg"
    assert (tmp_path / "uploads/events/1/a.jpg").read_bytes() == b"bytes"
    anyio.run(store.remove, "uploads/events/1/a.jpg")
    assert not (tmp_path / "uploads/events/1/a.jpg").exists()
    # Removing twice / path traversal never raises.
    anyio.run(store.remove, "uploads/events/1/a.jpg")
    anyio.run(store.remove, "../escape.jpg")


def test_factory_selection(tmp_path):
    from types import SimpleNamespace

    from app.services.storage import (
        LocalStorage,
        S3Storage,
        SupabaseStorage,
        get_storage,
    )

    assert isinstance(
        get_storage(SimpleNamespace(media_backend="local", local_upload_dir=str(tmp_path))),
        LocalStorage,
    )
    assert isinstance(
        get_storage(
            SimpleNamespace(
                media_backend="supabase",
                supabase_url="https://x.supabase.co",
                supabase_service_key="k",
                supabase_bucket="b",
            )
        ),
        SupabaseStorage,
    )
    with pytest.raises(StorageNotConfigured):
        get_storage(
            SimpleNamespace(
                media_backend="supabase",
                supabase_url="",
                supabase_service_key="",
                supabase_bucket="b",
            )
        )
    with pytest.raises(ValueError, match="Unsupported storage backend"):
        get_storage(SimpleNamespace(media_backend="r22"))


def test_s3_storage_mocked():
    import sys
    from types import ModuleType, SimpleNamespace
    from unittest.mock import MagicMock

    fake_boto3 = ModuleType("boto3")
    fake_client = MagicMock()
    fake_boto3.client = MagicMock(return_value=fake_client)
    sys.modules["boto3"] = fake_boto3
    try:
        from app.services.storage import S3Storage, get_storage, r2_public_base

        # Blank public base fails fast instead of storing unfetchable URLs.
        with pytest.raises(StorageNotConfigured):
            S3Storage("https://acc.r2.cloudflarestorage.com", "ak", "sk", "media", "")

        store = S3Storage(
            "https://acc.r2.cloudflarestorage.com",
            "ak",
            "sk",
            "media",
            "https://pub-abc.r2.dev",
        )
        assert store.public_url("uploads/a/b.jpg") == (
            "https://pub-abc.r2.dev/uploads/a/b.jpg"
        )
        # Upload and delete agree on the key via the shared helper.
        assert (
            r2_public_base("https://acc.r2.cloudflarestorage.com", "media", "https://pub-abc.r2.dev/")
            == "https://pub-abc.r2.dev"
        )
        import anyio

        url = anyio.run(store.upload, "uploads/a/b.jpg", b"data", "image/jpeg")
        assert url.endswith("/uploads/a/b.jpg")
        fake_client.put_object.assert_called_once()
        anyio.run(store.remove, "uploads/a/b.jpg")
        fake_client.delete_object.assert_called_once()

        via_factory = get_storage(
            SimpleNamespace(
                media_backend="r2",
                r2_endpoint="https://acc.r2.cloudflarestorage.com",
                r2_access_key="ak",
                r2_secret_key="sk",
                r2_bucket="media",
                r2_public_base="https://pub-abc.r2.dev",
            )
        )
        assert isinstance(via_factory, S3Storage)
        with pytest.raises(StorageNotConfigured):
            get_storage(
                SimpleNamespace(
                    media_backend="r2",
                    r2_endpoint="https://acc.r2.cloudflarestorage.com",
                    r2_access_key="ak",
                    r2_secret_key="sk",
                    r2_bucket="media",
                    r2_public_base="",
                )
            )
    finally:
        del sys.modules["boto3"]


def test_settings_rejects_unknown_backend():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(media_backend="r22")
    assert Settings(media_backend="R2").media_backend == "r2"
