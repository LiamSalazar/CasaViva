from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from apps.common.models import BusinessModel, UUIDTimeStampedModel, SourceRecord
from apps.geo.models import State, Municipality, Locality, Neighborhood
from apps.media_library.models import MediaAsset


class Developer(BusinessModel):
    name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=250, null=True, blank=True)
    slug = models.SlugField(max_length=220, unique=True)
    website = models.URLField(null=True, blank=True)
    logo_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="developer_logos")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        permissions = [("manage_developers", "Puede administrar desarrolladoras")]

    def __str__(self):
        return self.name


class Amenity(UUIDTimeStampedModel):
    class Category(models.TextChoices):
        DEVELOPMENT = "DEVELOPMENT", "Desarrollo"
        INTERIOR = "INTERIOR", "Interior"
        EXTERIOR = "EXTERIOR", "Exterior"
        SERVICE = "SERVICE", "Servicio"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=190, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Development(BusinessModel):
    developer = models.ForeignKey(Developer, on_delete=models.PROTECT, related_name="developments")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT)
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT)
    locality = models.ForeignKey(Locality, null=True, blank=True, on_delete=models.PROTECT)
    neighborhood = models.ForeignKey(Neighborhood, null=True, blank=True, on_delete=models.PROTECT)
    street_address = models.CharField(max_length=300, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False)
    amenities = models.ManyToManyField(Amenity, through="DevelopmentAmenity", blank=True)

    class Meta:
        indexes = [models.Index(fields=["developer"]), models.Index(fields=["state", "municipality"])]
        permissions = [("manage_developments", "Puede administrar desarrollos")]

    def clean(self):
        errors = {}
        if self.municipality_id and self.state_id and self.municipality.state_id != self.state_id:
            errors["municipality"] = "El municipio no pertenece al estado seleccionado."
        if self.locality_id and self.locality.municipality_id != self.municipality_id:
            errors["locality"] = "La localidad no pertenece al municipio seleccionado."
        if self.neighborhood_id and self.neighborhood.municipality_id != self.municipality_id:
            errors["neighborhood"] = "La colonia no pertenece al municipio seleccionado."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class HousingModel(BusinessModel):
    developer = models.ForeignKey(Developer, on_delete=models.PROTECT, related_name="housing_models")
    name = models.CharField(max_length=180)
    internal_code = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(max_length=230, unique=True, db_index=True)
    base_description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["developer", "archived_at"])]
        permissions = [("manage_models", "Puede administrar modelos")]

    def __str__(self):
        return self.name


class DevelopmentModel(BusinessModel):
    development = models.ForeignKey(Development, on_delete=models.PROTECT, related_name="model_links")
    housing_model = models.ForeignKey(HousingModel, on_delete=models.PROTECT, related_name="development_links")
    display_name_override = models.CharField(max_length=180, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["development", "housing_model"], condition=models.Q(archived_at__isnull=True), name="unique_active_development_model")]
        indexes = [models.Index(fields=["development", "housing_model"])]

    def clean(self):
        if self.development_id and self.housing_model_id and self.development.developer_id != self.housing_model.developer_id:
            raise ValidationError("El desarrollo y el modelo deben pertenecer a la misma desarrolladora.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.housing_model} — {self.development}"


class PropertyType(UUIDTimeStampedModel):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class PropertyOffering(BusinessModel):
    class SourceType(models.TextChoices):
        DEVELOPER = "DEVELOPER", "Desarrolladora"
        PRIVATE = "PRIVATE", "Particular"

    class AreaBasis(models.TextChoices):
        EXACT = "EXACT", "Exacta"
        UP_TO = "UP_TO", "Hasta"
        FROM = "FROM", "Desde"
        RANGE = "RANGE", "Rango"
        UNKNOWN = "UNKNOWN", "Desconocida"

    class Condition(models.TextChoices):
        NEW = "NEW", "Nueva"
        USED = "USED", "Usada"

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    condition = models.CharField(max_length=10, choices=Condition.choices, null=True, blank=True)
    development_model = models.ForeignKey(DevelopmentModel, null=True, blank=True, on_delete=models.PROTECT, related_name="offerings")
    variant_name = models.CharField(max_length=180, null=True, blank=True)
    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT, related_name="offerings")
    state = models.ForeignKey(State, null=True, blank=True, on_delete=models.PROTECT)
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.PROTECT)
    locality = models.ForeignKey(Locality, null=True, blank=True, on_delete=models.PROTECT)
    neighborhood = models.ForeignKey(Neighborhood, null=True, blank=True, on_delete=models.PROTECT)
    street_address = models.CharField(max_length=300, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    bedrooms_min = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    bedrooms_max = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    bathrooms_total = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    full_bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    half_bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    parking_min = models.PositiveSmallIntegerField(null=True, blank=True)
    parking_max = models.PositiveSmallIntegerField(null=True, blank=True)
    levels_min = models.PositiveSmallIntegerField(null=True, blank=True)
    levels_max = models.PositiveSmallIntegerField(null=True, blank=True)
    construction_area_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    construction_area_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    construction_area_basis = models.CharField(max_length=10, choices=AreaBasis.choices, null=True, blank=True)
    land_area_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    land_area_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    land_area_basis = models.CharField(max_length=10, choices=AreaBasis.choices, null=True, blank=True)
    garden_area_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    garden_area_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    garden_area_basis = models.CharField(max_length=10, choices=AreaBasis.choices, null=True, blank=True)
    internal_reference = models.CharField(max_length=100, null=True, blank=True)
    internal_notes = models.TextField(null=True, blank=True)
    default_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    amenities = models.ManyToManyField(Amenity, through="OfferingAmenity", blank=True, related_name="offerings")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(source_type="DEVELOPER", development_model__isnull=False) | models.Q(source_type="PRIVATE", development_model__isnull=True)), name="offering_source_requires_relation"),
            models.CheckConstraint(condition=models.Q(bedrooms_min__gte=0) | models.Q(bedrooms_min__isnull=True), name="offering_bedrooms_nonnegative"),
            models.CheckConstraint(condition=models.Q(bathrooms_total__gte=0) | models.Q(bathrooms_total__isnull=True), name="offering_bathrooms_nonnegative"),
            models.CheckConstraint(condition=models.Q(default_commission_rate__gte=0) | models.Q(default_commission_rate__isnull=True), name="offering_commission_nonnegative"),
            models.CheckConstraint(condition=models.Q(default_commission_rate__lte=100) | models.Q(default_commission_rate__isnull=True), name="offering_commission_max_100"),
            models.CheckConstraint(condition=models.Q(latitude__range=(-90, 90)) | models.Q(latitude__isnull=True), name="offering_latitude_valid"),
            models.CheckConstraint(condition=models.Q(longitude__range=(-180, 180)) | models.Q(longitude__isnull=True), name="offering_longitude_valid"),
            models.CheckConstraint(condition=models.Q(bedrooms_max__gte=models.F("bedrooms_min")) | models.Q(bedrooms_max__isnull=True) | models.Q(bedrooms_min__isnull=True), name="offering_bedrooms_range_valid"),
            models.CheckConstraint(condition=models.Q(parking_max__gte=models.F("parking_min")) | models.Q(parking_max__isnull=True) | models.Q(parking_min__isnull=True), name="offering_parking_range_valid"),
            models.CheckConstraint(condition=models.Q(levels_max__gte=models.F("levels_min")) | models.Q(levels_max__isnull=True) | models.Q(levels_min__isnull=True), name="offering_levels_range_valid"),
            models.CheckConstraint(condition=models.Q(construction_area_min__gte=0) | models.Q(construction_area_min__isnull=True), name="offering_construction_min_nonnegative"),
            models.CheckConstraint(condition=models.Q(construction_area_max__gte=0) | models.Q(construction_area_max__isnull=True), name="offering_construction_max_nonnegative"),
            models.CheckConstraint(condition=models.Q(construction_area_max__gte=models.F("construction_area_min")) | models.Q(construction_area_max__isnull=True) | models.Q(construction_area_min__isnull=True), name="offering_construction_range_valid"),
            models.CheckConstraint(condition=models.Q(land_area_min__gte=0) | models.Q(land_area_min__isnull=True), name="offering_land_min_nonnegative"),
            models.CheckConstraint(condition=models.Q(land_area_max__gte=0) | models.Q(land_area_max__isnull=True), name="offering_land_max_nonnegative"),
            models.CheckConstraint(condition=models.Q(land_area_max__gte=models.F("land_area_min")) | models.Q(land_area_max__isnull=True) | models.Q(land_area_min__isnull=True), name="offering_land_range_valid"),
            models.CheckConstraint(condition=models.Q(garden_area_min__gte=0) | models.Q(garden_area_min__isnull=True), name="offering_garden_min_nonnegative"),
            models.CheckConstraint(condition=models.Q(garden_area_max__gte=0) | models.Q(garden_area_max__isnull=True), name="offering_garden_max_nonnegative"),
            models.CheckConstraint(condition=models.Q(garden_area_max__gte=models.F("garden_area_min")) | models.Q(garden_area_max__isnull=True) | models.Q(garden_area_min__isnull=True), name="offering_garden_range_valid"),
        ]
        indexes = [models.Index(fields=["development_model"]), models.Index(fields=["property_type"]), models.Index(fields=["state", "municipality"]), models.Index(fields=["property_type", "bedrooms_min", "bathrooms_total"])]
        permissions = [("manage_offerings", "Puede administrar propiedades"), ("manage_catalogs", "Puede administrar catálogos")]

    def effective_location(self):
        development = self.development_model.development if self.development_model_id else None
        return {
            "state": self.state or (development.state if development else None),
            "municipality": self.municipality or (development.municipality if development else None),
            "locality": self.locality or (development.locality if development else None),
            "neighborhood": self.neighborhood or (development.neighborhood if development else None),
            "latitude": self.latitude if self.latitude is not None else (development.latitude if development else None),
            "longitude": self.longitude if self.longitude is not None else (development.longitude if development else None),
        }

    def clean(self):
        errors = {}
        development = self.development_model.development if self.development_model_id else None
        effective_state_id = self.state_id or (development.state_id if development else None)
        effective_municipality_id = self.municipality_id or (development.municipality_id if development else None)
        if self.municipality_id and effective_state_id and self.municipality.state_id != effective_state_id:
            errors["municipality"] = "El municipio no pertenece al estado seleccionado."
        if self.locality_id and effective_municipality_id and self.locality.municipality_id != effective_municipality_id:
            errors["locality"] = "La localidad no pertenece al municipio seleccionado."
        if self.neighborhood_id and effective_municipality_id and self.neighborhood.municipality_id != effective_municipality_id:
            errors["neighborhood"] = "La colonia no pertenece al municipio seleccionado."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        if self.development_model_id:
            return f"{self.development_model.housing_model.name}{' — ' + self.variant_name if self.variant_name else ''}"
        return self.internal_reference or f"Propiedad {self.pk}"


class DevelopmentAmenity(models.Model):
    development = models.ForeignKey(Development, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["development", "amenity"], name="unique_development_amenity")]


class OfferingAmenity(models.Model):
    offering = models.ForeignKey(PropertyOffering, on_delete=models.CASCADE, related_name="amenity_links")
    amenity = models.ForeignKey(Amenity, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["offering", "amenity"], name="unique_offering_amenity")]


class FeatureDefinition(UUIDTimeStampedModel):
    class DataType(models.TextChoices):
        BOOLEAN = "BOOLEAN", "Sí / No"
        NUMBER = "NUMBER", "Número"
        TEXT = "TEXT", "Texto"
        CHOICE = "CHOICE", "Opción"

    code = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=160)
    category = models.CharField(max_length=100)
    data_type = models.CharField(max_length=12, choices=DataType.choices)
    unit = models.CharField(max_length=30, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    is_filterable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.label


class FeatureChoice(UUIDTimeStampedModel):
    definition = models.ForeignKey(FeatureDefinition, on_delete=models.CASCADE, related_name="choices")
    value = models.CharField(max_length=120)
    label = models.CharField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["definition", "value"], name="unique_feature_choice_value")]


class OfferingFeatureValue(UUIDTimeStampedModel):
    offering = models.ForeignKey(PropertyOffering, on_delete=models.CASCADE, related_name="feature_values")
    definition = models.ForeignKey(FeatureDefinition, on_delete=models.PROTECT)
    value_boolean = models.BooleanField(null=True, blank=True)
    value_number = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    value_text = models.TextField(null=True, blank=True)
    value_choice = models.ForeignKey(FeatureChoice, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["offering", "definition"], name="unique_offering_feature")]

    def clean(self):
        values = [self.value_boolean is not None, self.value_number is not None, bool(self.value_text), self.value_choice_id is not None]
        if sum(values) != 1:
            raise ValidationError("Debe capturarse exactamente un valor tipado.")


class EntityMediaBase(models.Model):
    class Role(models.TextChoices):
        HERO = "HERO", "Portada"
        GALLERY = "GALLERY", "Galería"
        FLOORPLAN = "FLOORPLAN", "Plano"
        DOCUMENT = "DOCUMENT", "Documento"
    media = models.ForeignKey(MediaAsset, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class DevelopmentMedia(EntityMediaBase):
    development = models.ForeignKey(Development, on_delete=models.CASCADE, related_name="media_links")


class OfferingMedia(EntityMediaBase):
    offering = models.ForeignKey(PropertyOffering, on_delete=models.CASCADE, related_name="media_links")
