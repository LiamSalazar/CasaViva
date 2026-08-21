import pytest

from apps.content.models import Guide, LocationContent
from apps.catalog.models import Amenity, Development, DevelopmentMedia
from apps.geo.models import Locality, Neighborhood
from apps.media_library.models import MediaAsset


@pytest.mark.django_db
def test_location_editorial_content_crud_is_separate_from_geo_catalog(admin_client, catalog):
    municipality = catalog["municipality"]
    create = admin_client.post(
        "/api/v1/admin/location-content/",
        {
            "municipality": str(municipality.id), "slug": "tecamac-editorial",
            "description": "Contenido editorial de Tecámac", "is_featured": True,
            "latitude": "19.712345", "longitude": "-98.998765",
        },
        format="json",
    )
    assert create.status_code == 201, create.data
    content = LocationContent.objects.get(municipality=municipality)
    assert content.description == "Contenido editorial de Tecámac"

    public = admin_client.get("/api/v1/public/locations/")
    municipality_data = next(item for state in public.data for item in state["municipalities"] if str(item["id"]) == str(municipality.id))
    assert municipality_data["slug"] == "tecamac-editorial"
    assert municipality_data["description"] == "Contenido editorial de Tecámac"
    assert municipality_data["content_id"] == content.id
    assert "version" not in municipality_data

    update = admin_client.patch(
        f"/api/v1/admin/location-content/{content.id}/",
        {"description": "Texto corregido", "version": content.version},
        format="json",
    )
    assert update.status_code == 200
    content.refresh_from_db()
    assert content.description == "Texto corregido"

    delete = admin_client.delete(f"/api/v1/admin/location-content/{content.id}/")
    assert delete.status_code == 204
    content.refresh_from_db()
    assert content.archived_at is not None
    assert type(municipality).objects.filter(pk=municipality.pk).exists()
    public_after = admin_client.get("/api/v1/public/locations/")
    municipality_after = next(item for state in public_after.data for item in state["municipalities"] if str(item["id"]) == str(municipality.id))
    assert municipality_after["content_id"] is None


@pytest.mark.django_db
def test_draft_guide_is_admin_only_until_published(admin_client):
    create = admin_client.post(
        "/api/v1/admin/guides/",
        {"slug": "guia-borrador", "title": "Guía borrador", "excerpt": "", "content": "Contenido", "category": "zonas", "published": False, "featured": False},
        format="json",
    )
    assert create.status_code == 201, create.data
    guide = Guide.objects.get(slug="guia-borrador")
    assert admin_client.get("/api/v1/admin/guides/").status_code == 200
    assert admin_client.get("/api/v1/public/guides/guia-borrador/").status_code == 404
    publish = admin_client.patch(
        f"/api/v1/admin/guides/{guide.id}/",
        {"published": True, "version": guide.version},
        format="json",
    )
    assert publish.status_code == 200
    assert admin_client.get("/api/v1/public/guides/guia-borrador/").status_code == 200


@pytest.mark.django_db
def test_draft_development_is_visible_in_admin_not_public(admin_client, catalog):
    development = catalog["development"]
    assert admin_client.get(f"/api/v1/admin/developments/{development.id}/").status_code == 200
    assert admin_client.get(f"/api/v1/public/developments/{development.slug}/").status_code == 404
    response = admin_client.patch(
        f"/api/v1/admin/developments/{development.id}/",
        {"is_published": True, "version": development.version},
        format="json",
    )
    assert response.status_code == 200
    assert admin_client.get(f"/api/v1/public/developments/{development.slug}/").status_code == 200


@pytest.mark.django_db
def test_development_form_fields_round_trip(admin_client, owner, catalog):
    locality = Locality.objects.create(municipality=catalog["municipality"], name="Localidad Centro")
    neighborhood = Neighborhood.objects.create(municipality=catalog["municipality"], locality=locality, name="Colonia Centro", postal_code="55749")
    amenity = Amenity.objects.create(name="Casa club", slug="casa-club", category="DEVELOPMENT")
    media = MediaAsset.objects.create(
        storage_key="media/development.webp", media_type="IMAGE", original_filename="development.webp",
        mime_type="image/webp", byte_size=100, width=100, height=80, sha256="a" * 64, uploaded_by=owner,
    )
    response = admin_client.post(
        "/api/v1/admin/developments/",
        {
            "developer": str(catalog["developer"].id), "name": "Desarrollo completo", "slug": "desarrollo-completo",
            "state": str(catalog["state"].id), "municipality": str(catalog["municipality"].id),
            "locality": str(locality.id), "neighborhood": str(neighborhood.id),
            "street_address": "Avenida Principal 10", "postal_code": "55749",
            "latitude": "19.612345", "longitude": "-99.012345",
            "short_description": "Breve", "description": "Completa", "is_published": False, "is_featured": True,
            "amenity_ids": [str(amenity.id)],
            "media_input": [{"media_id": str(media.id), "role": "HERO", "sort_order": 0}],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    development = Development.objects.get(slug="desarrollo-completo")
    assert development.locality == locality
    assert development.neighborhood == neighborhood
    assert development.street_address == "Avenida Principal 10"
    assert development.postal_code == "55749"
    assert list(development.amenities.values_list("name", flat=True)) == ["Casa club"]
    assert DevelopmentMedia.objects.get(development=development).media == media
    detail = admin_client.get(f"/api/v1/admin/developments/{development.id}/")
    assert detail.data["amenity_ids"] == [amenity.id]
    assert detail.data["media"][0]["role"] == "HERO"
