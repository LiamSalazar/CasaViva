from django.db import models
from apps.common.models import BusinessModel
from apps.media_library.models import MediaAsset


class HomeContent(BusinessModel):
    key = models.CharField(max_length=40, unique=True, default="main")
    hero_eyebrow = models.CharField(max_length=120, blank=True)
    hero_title = models.CharField(max_length=240)
    editorial_title = models.CharField(max_length=240, blank=True)
    editorial_body = models.TextField(blank=True)
    editorial_media = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        permissions = [("manage_content", "Puede administrar contenido público")]


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
