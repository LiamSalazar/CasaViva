from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.services import seed_groups
from apps.catalog.models import Amenity, FeatureDefinition, PropertyType
from apps.crm.models import PrivacyNoticeVersion, TermsOfUseVersion
from apps.content.models import AboutContent, SiteSettings
import hashlib
from datetime import datetime


class Command(BaseCommand):
    help = "Crea roles, permisos y catálogos controlados iniciales sin sobrescribir cambios humanos."

    @transaction.atomic
    def handle(self, *args, **options):
        seed_groups()
        for order, (code, name) in enumerate([("house", "Casa"), ("apartment", "Departamento"), ("land", "Terreno"), ("townhouse", "Townhouse")]):
            PropertyType.objects.get_or_create(code=code, defaults={"name": name, "sort_order": order})
        for order, (name, category) in enumerate([
            ("Áreas verdes", "DEVELOPMENT"), ("Juegos infantiles", "DEVELOPMENT"),
            ("Acceso controlado", "SERVICE"), ("Jardín", "EXTERIOR"),
            ("Balcón", "EXTERIOR"), ("Bodega", "INTERIOR"), ("Cuarto de lavado", "INTERIOR"),
            ("Patio de servicio", "EXTERIOR"), ("Vestidor", "INTERIOR"),
        ]):
            slug = name.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace(" ", "-")
            Amenity.objects.get_or_create(slug=slug, defaults={"name": name, "category": category, "sort_order": order})
        FeatureDefinition.objects.get_or_create(code="area-tv-home-office", defaults={"label": "Área de TV / Home Office", "category": "Interior", "data_type": "BOOLEAN", "is_public": True})
        SiteSettings.objects.get_or_create(
            key="main",
            defaults={
                "contact_email": "casavivabyana@gmail.com",
                "facebook_url": "https://www.facebook.com/share/1HNjVPdtWy/",
                "instagram_url": "https://www.instagram.com/casaacbviva.inmuebles?igsi=YzA5aDBsdW9vbnox",
                "tiktok_url": "https://www.tiktok.com/@ana.casaviva?_r=1&_t=ZS-999Ov10JJcD",
            },
        )
        AboutContent.objects.get_or_create(key="main", defaults={
            "eyebrow": "CasaViva", "hero_title": "Una forma más clara de encontrar hogar.",
            "main_title": "Promocionar bien también es informar mejor.",
            "main_body": "CasaViva reúne y promociona propiedades de desarrolladoras y propietarios particulares para facilitar su exploración y acercar a las personas interesadas con el proveedor correspondiente.",
            "what_we_do_title": "Qué hacemos", "what_we_do_body": "Presentamos propiedades de forma visual y ordenada, ayudamos a comparar opciones y canalizamos las solicitudes de información hacia quien comercializa cada inmueble.",
            "how_we_work_title": "Cómo trabajamos", "how_we_work_body": "Trabajamos como promotores externos. La información publicada parte de los datos proporcionados o autorizados por desarrolladoras y propietarios, y buscamos mantener precios, disponibilidad y características actualizados.",
            "vision_title": "Nuestra visión", "vision_body": "Queremos que encontrar una vivienda sea un proceso más claro, con mejor información, herramientas útiles y seguimiento oportuno.",
        })
        current_notice = (
            "CasaViva trata la información proporcionada para atender consultas, coordinar visitas y dar seguimiento a solicitudes inmobiliarias.\n"
            "Los formularios solicitan únicamente los datos necesarios para responder. El consentimiento y la versión del aviso aplicable se conservan como parte del historial de atención."
        )
        legacy, _ = PrivacyNoticeVersion.objects.get_or_create(
            version="web-2026-08-01",
            defaults={"title": "Aviso de privacidad", "body": current_notice, "published_at": timezone.make_aware(datetime(2026, 8, 1, 0, 0)), "effective_at": timezone.make_aware(datetime(2026, 8, 1, 0, 0)), "status": "PUBLISHED", "content_hash": hashlib.sha256(current_notice.encode()).hexdigest(), "is_active": True},
        )
        if legacy and not legacy.body:
            if legacy.content_hash == hashlib.sha256(current_notice.encode()).hexdigest():
                PrivacyNoticeVersion.objects.filter(pk=legacy.pk).update(title="Aviso de privacidad", body=current_notice, status="PUBLISHED", historical_content_available=True)
            else:
                PrivacyNoticeVersion.objects.filter(pk=legacy.pk).update(status="RETIRED", is_active=False, historical_content_available=False)
        PrivacyNoticeVersion.objects.get_or_create(version="integral-2026-draft", defaults={"title": "AVISO DE PRIVACIDAD INTEGRAL DE CASAVIVA", "body": PRIVACY_DRAFT, "status": "DRAFT", "is_active": False})
        TermsOfUseVersion.objects.get_or_create(version="terms-2026-draft", defaults={"title": "TÉRMINOS DE USO DE CASAVIVA", "body": TERMS_DRAFT, "status": "DRAFT", "is_active": False})
        self.stdout.write(self.style.SUCCESS("Catálogos y roles iniciales listos."))


PRIVACY_DRAFT = """Responsable del tratamiento

José Alfredo Salazar Hernández, quien opera el sitio y plataforma denominada CasaViva, con domicilio en [DOMICILIO DEL RESPONSABLE], es responsable del tratamiento de los datos personales recabados a través de CasaViva.

CasaViva funciona actualmente como plataforma de promoción inmobiliaria y captación de personas interesadas. CasaViva promociona inmuebles de desarrolladoras y propietarios particulares y canaliza las solicitudes de los interesados hacia el proveedor o propietario correspondiente. CasaViva no es propietaria ni desarrolladora de los inmuebles publicados y no celebra mediante este sitio el contrato de compraventa de las viviendas.

## Datos personales que podemos recabar

Podremos recabar nombre, correo electrónico, número telefónico, mensaje o consulta, inmueble, desarrollo o zona de interés, preferencias de búsqueda e información relacionada con solicitudes de visita o seguimiento. El sitio puede generar identificadores temporales de sesión, fecha y hora, páginas o propiedades consultadas, búsquedas, filtros, fuente de llegada, parámetros de campaña, tipo general de dispositivo y registros técnicos de seguridad. CasaViva no solicita intencionalmente datos sensibles.

## Finalidades primarias

Recibir y responder solicitudes; identificar el inmueble o búsqueda; ayudar a localizar opciones; contactar; coordinar visitas; dar seguimiento; canalizar los datos estrictamente necesarios al proveedor autorizado; conservar historial; medir internamente el sitio y resultados comerciales; mantener seguridad; y acreditar autorizaciones y consentimientos.

## Finalidades secundarias

CasaViva no enviará boletines, promociones generales o publicidad ajena a la solicitud sin autorización separada. El seguimiento razonablemente relacionado con la solicitud no se considera publicidad secundaria.

## Transferencias y canalización

Para atender una solicitud concreta, CasaViva podrá transferir los datos estrictamente necesarios al desarrollador, propietario o proveedor correspondiente, exclusivamente para atención, seguimiento, visita y eventual operación solicitada. La canalización se informará expresamente y registrará de forma independiente. Los encargados tecnológicos sólo procesarán datos por instrucciones de CasaViva.

## Limitación, derechos ARCO y revocación

Puede limitar el uso y divulgación, ejercer acceso, rectificación, cancelación u oposición, o revocar consentimientos escribiendo a [CORREO DE PRIVACIDAD]. La solicitud debe identificar a la persona, un medio de respuesta, acreditar razonablemente identidad, describir los datos y el derecho. CasaViva responderá dentro de los plazos legales aplicables. La revocación no tendrá efectos retroactivos.

## Conservación, seguridad y confidencialidad

Los datos se conservarán sólo durante el tiempo necesario para las finalidades, responsabilidades y obligaciones aplicables; después se bloquearán, anonimizarán o eliminarán según corresponda. CasaViva aplica medidas administrativas y técnicas, cuentas autorizadas, permisos y autenticación adicional.

## Analítica y almacenamiento técnico

CasaViva utiliza almacenamiento local o de sesión de primera parte para funcionamiento, procedencia y medición interna. No incorporará píxeles publicitarios de Google, Meta, TikTok u otros sin revisión, actualización del aviso y consentimiento aplicable. El visitante puede limitar la analítica no indispensable.

## Cambios y contacto

La versión vigente estará permanentemente en /aviso-de-privacidad y mostrará versión y vigencia. Contacto de privacidad: José Alfredo Salazar Hernández, [CORREO DE PRIVACIDAD], [DOMICILIO DEL RESPONSABLE]."""

TERMS_DRAFT = """1. Identificación y objeto del sitio

CasaViva es una plataforma operada por José Alfredo Salazar Hernández cuya función actual consiste en promocionar inmuebles de terceros, facilitar su consulta y captar y canalizar personas interesadas hacia los desarrolladores, propietarios o proveedores correspondientes.

2. Alcance de CasaViva

CasaViva actúa como promotor externo. No es propietaria ni desarrolladora; no celebra mediante el sitio la compraventa; no recibe enganches, apartados o pagos para adquirir vivienda; no presta servicios notariales; no otorga financiamiento ni garantiza créditos. La operación se formaliza directamente con el proveedor.

3. Información de las propiedades

La información procede de fuentes proporcionadas o autorizadas por proveedores. CasaViva realizará esfuerzos razonables para mantener precios, disponibilidad, dimensiones, características y fotografías actualizados y no publicará deliberadamente información sin fuente autorizada. Deben confirmarse las condiciones vigentes con el proveedor antes de contratar.

4. Precios y promociones

Los precios se muestran en pesos mexicanos como fijo, desde, rango o a consultar. Las promociones, descuentos o beneficios mostrarán condiciones y vigencia aplicables.

5. Desarrolladoras y propietarios

Cada ficha identificará razonablemente al proveedor o indicará propietario particular. La publicación no significa que CasaViva sea propietaria.

6. Solicitudes y visitas

CasaViva puede responder, orientar, coordinar visitas, dar seguimiento y canalizar al proveedor. El tratamiento y transferencia se rigen por el Aviso vigente. Una visita no es reserva, compraventa, promesa ni garantía de disponibilidad.

7. Financiamiento y pagos

CasaViva puede mostrar información general o facilitar, a solicitud, contacto con terceros independientes. No es institución financiera ni garantiza condiciones o aprobación. CasaViva no solicita mediante el sitio pagos para reservar o adquirir propiedades.

8. Financiamiento

CasaViva puede mostrar información general sobre formas de adquisición o, cuando el usuario lo solicite, facilitar el contacto con terceros independientes relacionados con financiamiento. CasaViva no es una institución financiera y no garantiza tasas, montos, condiciones ni aprobación de crédito. Cualquier producto financiero será responsabilidad exclusiva del proveedor que lo ofrezca y estará sujeto a sus propios términos.

9. No recepción de pagos

En su modalidad actual, CasaViva no solicita mediante el sitio pagos para reservar o adquirir propiedades. El visitante no deberá realizar depósitos a cuentas que se presenten como pertenecientes a CasaViva para adquirir una vivienda, salvo que en el futuro exista una funcionalidad expresamente implementada, documentada y amparada por términos actualizados.

10. Uso permitido

El sitio puede utilizarse para consultar información, comparar propiedades, realizar búsquedas, guardar favoritos, solicitar atención y utilizar las demás funciones legítimamente habilitadas. No está permitido intentar acceder sin autorización a áreas administrativas; interferir con el funcionamiento; automatizar extracción masiva abusiva; cargar contenido malicioso; utilizar la plataforma con fines fraudulentos; ni hacerse pasar por otra persona.

11. Contenido e imágenes

Las fotografías, planos, logotipos, textos y demás materiales pueden pertenecer a CasaViva, desarrolladoras, propietarios u otros titulares que hayan autorizado su utilización. La publicación en CasaViva no implica una cesión de derechos al visitante.

12. Enlaces y servicios de terceros

El sitio puede dirigir al usuario hacia servicios, proveedores o sitios externos. CasaViva no controla las plataformas de terceros y el uso de éstas estará sujeto a sus propios términos y avisos.

13. Privacidad

El tratamiento de datos personales se rige por el Aviso de Privacidad vigente disponible permanentemente en la plataforma.

14. Disponibilidad tecnológica

CasaViva procura mantener el sitio disponible y seguro, pero pueden existir interrupciones derivadas de mantenimiento, fallas técnicas, servicios de terceros o causas fuera de control razonable.

15. Cambios

CasaViva puede modificar estos Términos cuando cambien las funcionalidades o la forma de operar. Cada versión publicada deberá indicar número de versión y fecha de entrada en vigor. Las nuevas versiones no deberán modificar retrospectivamente operaciones ya formalizadas con terceros.

16. Contacto y quejas

[CORREO DE CONTACTO O QUEJAS]

[TELÉFONO DE CONTACTO]

17. Legislación aplicable

Estos Términos se interpretarán conforme a la legislación aplicable de los Estados Unidos Mexicanos."""
