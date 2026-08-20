from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.common.exports import csv_response
from .models import Inquiry, Lead, Sale, Visit
from .serializers import InquirySerializer, LeadSerializer, PublicInquirySerializer, SaleSerializer, VisitSerializer
from drf_spectacular.utils import extend_schema, OpenApiTypes


class InquiryThrottle(ScopedRateThrottle): scope = "inquiry"

@extend_schema(request=PublicInquirySerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([InquiryThrottle])
def public_inquiry(request):
    serializer = PublicInquirySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inquiry = serializer.save()
    return Response({"id": inquiry.id, "message": "Recibimos tu consulta. Te contactaremos pronto."}, status=201)


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_leads"
    queryset = Lead.objects.select_related("owner_user")
    serializer_class = LeadSerializer
    filterset_fields = ["status", "owner_user"]
    search_fields = ["first_name", "last_name", "email", "phone_normalized"]

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[x.first_name, x.last_name or "", x.email or "", x.phone_raw or "", x.get_status_display(), x.created_at.isoformat()] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("clientes.csv", ["Nombre", "Apellidos", "Correo", "Teléfono", "Estado", "Creado"], rows)

class InquiryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_inquiries"
    queryset = Inquiry.objects.select_related("lead", "listing", "assigned_to")
    serializer_class = InquirySerializer
    filterset_fields = ["status", "channel", "assigned_to"]
    search_fields = ["lead__first_name", "lead__last_name", "lead__email", "message"]

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[str(x.id), str(x.lead), x.get_channel_display(), x.get_status_display(), x.listing.title if x.listing else "", x.created_at.isoformat()] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("consultas.csv", ["Identificador", "Cliente", "Canal", "Estado", "Propiedad", "Creada"], rows)

class VisitViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_visits"
    queryset = Visit.objects.select_related("lead", "offering", "assigned_to")
    serializer_class = VisitSerializer
    filterset_fields = ["status", "assigned_to"]

class SaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_sales"
    queryset = Sale.objects.select_related("lead", "offering", "listing")
    serializer_class = SaleSerializer
    filterset_fields = ["status", "closed_at"]

    def perform_create(self, serializer):
        rate = serializer.validated_data.get("commission_rate") or serializer.validated_data["offering"].default_commission_rate
        amount = serializer.validated_data["sale_price"] * rate / 100 if rate is not None else None
        serializer.save(created_by=self.request.user, commission_rate=rate, commission_amount=amount)

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[str(x.id), str(x.lead), str(x.offering), x.sale_price, x.commission_rate if x.commission_rate is not None else "", x.commission_amount if x.commission_amount is not None else "", x.closed_at.isoformat(), x.status] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("ventas.csv", ["Identificador", "Cliente", "Propiedad", "Precio de venta", "Comisión %", "Comisión", "Cierre", "Estado"], rows)
