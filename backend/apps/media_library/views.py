from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from .models import MediaAsset
from .services import store_upload
from drf_spectacular.utils import extend_schema, OpenApiTypes

@extend_schema(request=OpenApiTypes.BINARY, responses={201: OpenApiTypes.OBJECT})
@api_view(["GET", "POST"])
@permission_classes([IsMfaVerifiedAdmin])
def upload_media(request):
    if not request.user.is_superuser and not (
        request.user.has_perm("catalog.manage_offerings") or request.user.has_perm("content.manage_content")
    ):
        return Response({"detail": "No tienes permiso para administrar multimedia."}, status=403)
    if request.method == "GET":
        assets = MediaAsset.objects.order_by("-created_at")[:100]
        return Response({"results": [
            {"id": str(asset.id), "url": asset.url, "media_type": asset.media_type,
             "original_filename": asset.original_filename, "alt_text": asset.alt_text}
            for asset in assets
        ]})
    upload = request.FILES.get("file")
    if not upload:
        return Response({"detail": "Selecciona un archivo."}, status=400)
    asset = store_upload(upload, request.user, media_type=request.data.get("media_type", "IMAGE"), alt_text=request.data.get("alt_text"))
    return Response({"id": asset.id, "url": asset.url, "width": asset.width, "height": asset.height}, status=201)
