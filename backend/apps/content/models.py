from django.db import models
from apps.common.models import BusinessModel
from apps.media_library.models import MediaAsset
from apps.geo.models import Municipality


class HomeContent(BusinessModel):
    key = models.CharField(max_length=40, unique=True, default="main")
    hero_eyebrow = models.CharField(max_length=120, blank=True)
    hero_title = models.CharField(max_length=240)
    editorial_title = models.CharField(max_length=240, blank=True)
    editorial_body = models.TextField(blank=True)
    editorial_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        permissions = [("manage_content", "Puede administrar contenido público")]


class SiteSettings(BusinessModel):
    key = models.CharField(max_length=40, unique=True, default="main")
    brand_name = models.CharField(max_length=120, default="CasaViva")
    responsible_name = models.CharField(max_length=200, default="José Alfredo Salazar Hernández")
    operator_type = models.CharField(max_length=30, default="PERSONA_FISICA")
    commercial_role = models.CharField(max_length=30, default="EXTERNAL_PROMOTER")
    commercial_role_display = models.CharField(max_length=120, default="Promotor externo")
    responsible_address = models.TextField(blank=True)
    privacy_email = models.EmailField(blank=True)
    contact_email = models.EmailField(blank=True)
    complaints_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    verification_warning_days = models.PositiveIntegerField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    tiktok_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return "Información de contacto de CasaViva"

    class Meta:
        permissions = [("manage_legal_identity", "Puede administrar la identidad legal de CasaViva")]


class AboutContent(BusinessModel):
    key = models.CharField(max_length=40, unique=True, default="main")
    eyebrow = models.CharField(max_length=120, blank=True)
    hero_title = models.CharField(max_length=240)
    hero_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="about_heroes")
    main_title = models.CharField(max_length=240)
    main_body = models.TextField()
    what_we_do_title = models.CharField(max_length=240)
    what_we_do_body = models.TextField()
    how_we_work_title = models.CharField(max_length=240)
    how_we_work_body = models.TextField()
    vision_title = models.CharField(max_length=240)
    vision_body = models.TextField()
    cta_label = models.CharField(max_length=120, blank=True)
    cta_url = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return "Contenido de Nosotros"


class HomeHeroSlide(BusinessModel):
    home_content = models.ForeignKey(HomeContent, on_delete=models.PROTECT, related_name="hero_slides")
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="home_hero_slides")
    eyebrow_override = models.CharField(max_length=120, null=True, blank=True)
    title_override = models.CharField(max_length=240, null=True, blank=True)
    subtitle_override = models.CharField(max_length=500, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        constraints = [models.UniqueConstraint(fields=["home_content", "listing"], name="unique_home_listing_slide")]


class Guide(BusinessModel):
    slug = models.SlugField(max_length=230, unique=True)
    title = models.CharField(max_length=240)
    excerpt = models.TextField(blank=True)
    content = models.TextField(blank=True)
    category = models.CharField(max_length=80)
    hero_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL)
    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class LocationContent(BusinessModel):
    municipality = models.OneToOneField(Municipality, on_delete=models.PROTECT, related_name="location_content")
    slug = models.SlugField(max_length=230, unique=True)
    description = models.TextField(blank=True)
    hero_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="location_heroes")
    is_featured = models.BooleanField(default=False, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.municipality.name
