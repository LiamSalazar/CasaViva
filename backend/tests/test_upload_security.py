import base64
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from apps.media_library.models import MediaAsset


def image_bytes(image_format="PNG"):
    output = io.BytesIO()
    Image.new("RGB", (20, 10), color="white").save(output, format=image_format)
    return output.getvalue()


@pytest.mark.django_db
def test_valid_image_is_reprocessed_and_stored(admin_client, tmp_path):
    upload = SimpleUploadedFile("portada.png", image_bytes(), content_type="image/png")
    with override_settings(MEDIA_ROOT=tmp_path):
        response = admin_client.post("/api/v1/admin/media/", {"file": upload, "media_type": "IMAGE"}, format="multipart")
    assert response.status_code == 201, response.data
    asset = MediaAsset.objects.get(pk=response.data["id"])
    assert asset.mime_type == "image/webp"
    assert asset.width == 20 and asset.height == 10
    assert asset.storage_key.endswith(".webp")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "content", "content_type"),
    [
        ("malware.jpg", b"MZ" + b"x" * 100, "image/jpeg"),
        ("pagina.html", b"<html><script>alert(1)</script></html>", "text/html"),
        ("codigo.js", b"alert('x')", "application/javascript"),
        ("corrupta.jpg", b"\xff\xd8\xffbroken", "image/jpeg"),
        ("crc-invalido.png", base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZL8sAAAAASUVORK5CYII="), "image/png"),
        ("falso.jpg", b"%PDF-1.4\n%test", "image/jpeg"),
    ],
)
def test_disguised_corrupt_and_executable_uploads_are_rejected(admin_client, tmp_path, name, content, content_type):
    upload = SimpleUploadedFile(name, content, content_type=content_type)
    with override_settings(MEDIA_ROOT=tmp_path):
        response = admin_client.post("/api/v1/admin/media/", {"file": upload, "media_type": "IMAGE"}, format="multipart")
    assert response.status_code == 400
    assert MediaAsset.objects.count() == 0


@pytest.mark.django_db
def test_valid_image_with_executable_extension_is_rejected(admin_client, tmp_path):
    upload = SimpleUploadedFile("imagen.exe", image_bytes(), content_type="image/png")
    with override_settings(MEDIA_ROOT=tmp_path):
        response = admin_client.post("/api/v1/admin/media/", {"file": upload, "media_type": "IMAGE"}, format="multipart")
    assert response.status_code == 400


@pytest.mark.django_db
def test_oversized_upload_is_rejected_before_storage(admin_client, tmp_path):
    upload = SimpleUploadedFile("grande.png", image_bytes() + b"x" * 100, content_type="image/png")
    with override_settings(MEDIA_ROOT=tmp_path, MAX_IMAGE_BYTES=20):
        response = admin_client.post("/api/v1/admin/media/", {"file": upload, "media_type": "IMAGE"}, format="multipart")
    assert response.status_code == 400
    assert MediaAsset.objects.count() == 0
