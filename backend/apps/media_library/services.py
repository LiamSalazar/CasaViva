import hashlib
import io
import uuid
from pathlib import Path
import filetype
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.exceptions import ValidationError
from .models import MediaAsset

ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
ALLOWED_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
}


def store_upload(upload, actor, media_type=MediaAsset.Type.IMAGE, alt_text=None):
    if media_type not in MediaAsset.Type.values:
        raise ValidationError("Selecciona un tipo de multimedia válido.")
    data = upload.read(settings.MAX_IMAGE_BYTES + 1)
    if len(data) > settings.MAX_IMAGE_BYTES:
        raise ValidationError("El archivo excede el tamaño permitido.")
    kind = filetype.guess(data)
    mime = kind.mime if kind else None
    if mime not in ALLOWED:
        raise ValidationError("El tipo de archivo no está permitido.")
    original_extension = Path(upload.name).suffix.lower()
    if original_extension not in ALLOWED_EXTENSIONS[mime]:
        raise ValidationError("La extensión no coincide con el contenido del archivo.")
    if mime == "application/pdf" and media_type not in (MediaAsset.Type.DOCUMENT, MediaAsset.Type.FLOORPLAN):
        raise ValidationError("Un PDF sólo puede registrarse como documento o plano.")
    if mime == "application/pdf" and not data.rstrip().endswith(b"%%EOF"):
        raise ValidationError("El documento PDF está dañado.")
    if mime.startswith("image/") and media_type not in (MediaAsset.Type.IMAGE, MediaAsset.Type.FLOORPLAN):
        raise ValidationError("El tipo de multimedia no corresponde a una imagen.")
    width = height = None
    extension = kind.extension
    if mime.startswith("image/"):
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            image = Image.open(io.BytesIO(data)).convert("RGB")
            width, height = image.size
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=88, method=6)
            data, mime, extension = output.getvalue(), "image/webp", "webp"
        except (UnidentifiedImageError, OSError):
            raise ValidationError("La imagen está dañada.")
    digest = hashlib.sha256(data).hexdigest()
    key = f"media/{uuid.uuid4()}.{extension}"
    default_storage.save(key, ContentFile(data))
    return MediaAsset.objects.create(storage_key=key, media_type=media_type, original_filename=Path(upload.name).name, mime_type=mime, byte_size=len(data), width=width, height=height, sha256=digest, alt_text=alt_text, uploaded_by=actor)
