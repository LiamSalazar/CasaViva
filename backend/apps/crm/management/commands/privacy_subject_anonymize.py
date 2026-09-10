import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.crm.management.commands.privacy_subject_lookup import subject_report
from apps.crm.models import Lead


class Command(BaseCommand):
    help = "Anonimiza datos de contacto; dry-run por defecto y preserva evidencias."
    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--phone")
        parser.add_argument("--confirm", action="store_true")
    @transaction.atomic
    def handle(self, *args, **options):
        report = subject_report(options["email"], options["phone"])
        if not options["confirm"]:
            self.stdout.write(json.dumps({"dry_run": True, "would_anonymize": report, "preserved": ["ConsentRecord", "AuditEvent", "Sale", "relaciones PROTECT"]}, ensure_ascii=False, indent=2)); return
        if not report["leads"]: raise CommandError("No se encontraron registros.")
        for item in report["leads"]:
            lead = Lead.all_objects.get(pk=item["id"])
            lead.first_name, lead.last_name, lead.email, lead.phone_raw, lead.phone_normalized = "Persona", "anonimizada", None, None, None
            lead.inquiries.update(message="[contenido anonimizado por solicitud revisada]")
            lead.save(update_fields=["first_name", "last_name", "email", "phone_raw", "phone_normalized", "updated_at"])
        self.stdout.write(json.dumps({"dry_run": False, "anonymized_leads": [x["id"] for x in report["leads"]], "preserved": ["ConsentRecord", "AuditEvent", "Sale", "relaciones PROTECT"]}, ensure_ascii=False, indent=2))
