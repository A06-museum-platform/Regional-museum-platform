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
