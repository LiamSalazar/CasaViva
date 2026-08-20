from django.db import models
from apps.common.models import UUIDTimeStampedModel


class State(UUIDTimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Municipality(UUIDTimeStampedModel):
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="municipalities")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["state", "name"], name="unique_municipality_state")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Locality(UUIDTimeStampedModel):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, related_name="localities")
    name = models.CharField(max_length=140)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["municipality", "name"], name="unique_locality_municipality")]

    def __str__(self):
        return self.name


class Neighborhood(UUIDTimeStampedModel):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, related_name="neighborhoods")
    locality = models.ForeignKey(Locality, null=True, blank=True, on_delete=models.PROTECT, related_name="neighborhoods")
    name = models.CharField(max_length=140)
    postal_code = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["municipality", "name"], name="unique_neighborhood_municipality")]

    def __str__(self):
        return self.name
