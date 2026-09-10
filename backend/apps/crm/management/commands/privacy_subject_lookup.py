import json
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from apps.crm.models import Lead


def subject_report(email=None, phone=None):
    query = Q()
    if email: query |= Q(email__iexact=email.strip())
    if phone: query |= Q(phone_normalized=phone) | Q(phone_raw=phone)
    leads = Lead.all_objects.filter(query).prefetch_related("inquiries", "visits", "sales", "consents", "web_sessions__events")
    return {"query": {"email": email, "phone": phone}, "leads": [{"id": str(lead.id), "email": lead.email, "phone": lead.phone_normalized, "archived": bool(lead.archived_at), "inquiries": [str(x.id) for x in lead.inquiries.all()], "visits": [str(x.id) for x in lead.visits.all()], "sales": [str(x.id) for x in lead.sales.all()], "consents": [str(x.id) for x in lead.consents.all()], "sessions": [{"id": str(x.id), "events": x.events.count()} for x in lead.web_sessions.all()]} for lead in leads]}


class Command(BaseCommand):
    help = "Consulta datos de una persona; nunca modifica registros."
    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--phone")
    def handle(self, *args, **options):
        if not options["email"] and not options["phone"]: raise CommandError("Indica --email o --phone.")
        self.stdout.write(json.dumps(subject_report(options["email"], options["phone"]), ensure_ascii=False, indent=2))
