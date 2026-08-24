from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttling import FixedScopeThrottle
from apps.accounts.permissions import HasRequiredPermission, IsMfaVerifiedAdmin
from apps.common.exports import csv_response
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, require_current_version, restore_entity
from apps.audit.services import audit_event
from apps.analytics.models import WebSession
from .models import Inquiry, Lead, LeadStageHistory, Sale, Visit
from .serializers import InquirySerializer, LeadSerializer, PublicInquirySerializer, SaleSerializer, VisitSerializer
from .services import change_lead_stage, change_sale_status, change_visit_status, create_sale, create_visit
from drf_spectacular.utils import extend_schema, OpenApiTypes


class InquiryThrottle(FixedScopeThrottle): scope = "inquiry"

@extend_schema(request=PublicInquirySerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([InquiryThrottle])
def public_inquiry(request):
    serializer = PublicInquirySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inquiry = serializer.save()
    message = "Solicitud de visita enviada." if inquiry.intent == Inquiry.Intent.VISIT_REQUEST else "Recibimos tu consulta. Te contactaremos pronto."
    return Response({"id": inquiry.id, "message": message}, status=201)


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_leads"
    queryset = Lead.objects.select_related("owner_user").order_by("-created_at", "id")
    serializer_class = LeadSerializer
    filterset_fields = ["status", "owner_user"]
    search_fields = ["first_name", "last_name", "email", "phone_normalized"]

    @transaction.atomic
    def perform_create(self, serializer):
        lead = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        LeadStageHistory.objects.create(lead=lead, stage=lead.status, started_at=timezone.now(), changed_by=self.request.user)
        audit_event(self.request.user, "CREATE", lead, request=self.request)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        lead = Lead.all_objects.select_for_update().get(pk=self.get_object().pk)
        require_current_version(request.data.get("version"), lead.version)
        target_stage = request.data.get("status", lead.status)
        data = {key: value for key, value in request.data.items() if key not in ("status", "version")}
        if data:
            serializer = self.get_serializer(lead, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            lead = serializer.save(updated_by=request.user, version=lead.version + 1)
            audit_event(request.user, "UPDATE", lead, request=request)
        if target_stage != lead.status:
            lead = change_lead_stage(lead, target_stage, request.user)
        return Response(self.get_serializer(lead).data)

    def destroy(self, request, *args, **kwargs):
        archive_entity(self.get_object(), request.user)
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        lead = Lead.all_objects.get(pk=pk)
        restore_entity(lead, request.user)
        return Response(self.get_serializer(lead).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[x.first_name, x.last_name or "", x.email or "", x.phone_raw or "", x.get_status_display(), x.created_at.isoformat()] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("clientes.csv", ["Nombre", "Apellidos", "Correo", "Teléfono", "Estado", "Creado"], rows)

class CommercialHistoryViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    def perform_create(self, serializer):
        obj = serializer.save()
        audit_event(self.request.user, "CREATE", obj, request=self.request)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit_event(self.request.user, "UPDATE", obj, request=self.request)


class InquiryViewSet(CommercialHistoryViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_inquiries"
    _sessions = WebSession.objects.filter(pk=OuterRef("session_id"))
    queryset = Inquiry.objects.select_related("lead", "listing", "assigned_to").annotate(
        campaign=Subquery(_sessions.values("utm_campaign")[:1]),
        source=Subquery(_sessions.values("utm_source")[:1]),
    ).order_by("-created_at", "id")
    serializer_class = InquirySerializer
    filterset_fields = ["status", "channel", "intent", "assigned_to"]
    search_fields = ["lead__first_name", "lead__last_name", "lead__email", "message"]

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[str(x.id), str(x.lead), x.get_intent_display(), x.get_subject_display() if x.subject else "", x.get_channel_display(), x.get_status_display(), x.listing.title if x.listing else "", x.created_at.isoformat()] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("consultas.csv", ["Identificador", "Cliente", "Intención", "Motivo", "Canal", "Estado", "Propiedad", "Creada"], rows)

class VisitViewSet(CommercialHistoryViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_visits"
    queryset = Visit.objects.select_related("lead", "offering", "assigned_to").order_by("-scheduled_at", "id")
    serializer_class = VisitSerializer
    filterset_fields = ["status", "assigned_to"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = create_visit(actor=request.user, **serializer.validated_data)
        return Response(self.get_serializer(visit).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        visit = Visit.objects.select_for_update().get(pk=self.get_object().pk)
        data = request.data.copy()
        new_status = data.pop("status", visit.status)
        if data:
            serializer = self.get_serializer(visit, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            visit = serializer.save()
            audit_event(request.user, "UPDATE", visit, request=request)
        if new_status != visit.status:
            visit = change_visit_status(visit, new_status, request.user, request=request)
        return Response(self.get_serializer(visit).data)

class SaleViewSet(CommercialHistoryViewSet):
    permission_classes = [IsMfaVerifiedAdmin, HasRequiredPermission]
    required_permission = "crm.manage_sales"
    queryset = Sale.objects.select_related("lead", "offering", "listing").order_by("-closed_at", "id")
    serializer_class = SaleSerializer
    filterset_fields = ["status", "closed_at"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = create_sale(actor=request.user, **serializer.validated_data)
        return Response(self.get_serializer(sale).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if set(request.data) - {"status"}:
            return Response({"detail": "Después del cierre sólo puede cambiarse el estado de la venta."}, status=400)
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        sale = change_sale_status(serializer.instance, serializer.validated_data.get("status", serializer.instance.status), request.user, request=request)
        return Response(self.get_serializer(sale).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = [[str(x.id), str(x.lead), str(x.offering), x.sale_price, x.commission_rate if x.commission_rate is not None else "", x.commission_amount if x.commission_amount is not None else "", x.closed_at.isoformat(), x.status] for x in self.filter_queryset(self.get_queryset())]
        return csv_response("ventas.csv", ["Identificador", "Cliente", "Propiedad", "Precio de venta", "Comisión %", "Comisión", "Cierre", "Estado"], rows)
