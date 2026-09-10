import pytest

from django.core.management import call_command

from apps.content.models import Guide, HomeContent, HomeHeroSlide, LocationContent, SiteSettings
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
def test_site_settings_seed_is_idempotent_editable_and_public_contract_is_minimal(admin_client):
    call_command("seed_system")
    settings = SiteSettings.objects.get(key="main")
    assert settings.contact_email == "casavivabyana@gmail.com"
    assert settings.facebook_url == "https://www.facebook.com/share/1HNjVPdtWy/"
    assert settings.instagram_url == "https://www.instagram.com/casaacbviva.inmuebles?igsi=YzA5aDBsdW9vbnox"
    assert settings.tiktok_url == "https://www.tiktok.com/@ana.casaviva?_r=1&_t=ZS-999Ov10JJcD"

    changed = admin_client.patch(
        f"/api/v1/admin/site-settings/{settings.id}/",
        {"version": settings.version, "instagram_url": "https://example.test/casaviva"},
        format="json",
    )
    assert changed.status_code == 200, changed.data
    call_command("seed_system")
    settings.refresh_from_db()
    assert settings.instagram_url == "https://example.test/casaviva"
    invalid = admin_client.patch(
        f"/api/v1/admin/site-settings/{settings.id}/",
        {"version": settings.version, "facebook_url": "javascript:alert(1)"},
        format="json",
    )
    assert invalid.status_code == 400

    public = admin_client.get("/api/v1/public/site-settings/")
    assert public.status_code == 200
    assert set(public.data["results"][0]) == {
        "brand_name", "responsible_name", "operator_type", "commercial_role", "commercial_role_display",
        "contact_email", "facebook_url", "instagram_url", "tiktok_url",
    }


@pytest.mark.django_db
def test_public_guide_detail_does_not_depend_on_first_page(admin_client):
    for index in range(30):
        Guide.objects.create(
            slug=f"guia-{index:02d}", title=f"Guía {index:02d}", category="hogar",
            is_published=True,
        )
    first_page = admin_client.get("/api/v1/public/guides/")
    assert first_page.status_code == 200 and first_page.data["next"] is not None
    second_page_slug = "guia-00"
    assert all(item["slug"] != second_page_slug for item in first_page.data["results"])
    detail = admin_client.get(f"/api/v1/public/guides/{second_page_slug}/")
    assert detail.status_code == 200
    assert detail.data["slug"] == second_page_slug
    assert set(detail.data) == {
        "id", "slug", "title", "excerpt", "content", "category", "heroImage",
        "published", "featured", "createdAt",
    }
    assert "version" not in detail.data and "hero_media" not in detail.data

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
def test_home_content_slides_and_editorial_media_round_trip(admin_client, owner, catalog):
    media = MediaAsset.objects.create(storage_key="home/editorial.webp", media_type="IMAGE", original_filename="editorial.webp", mime_type="image/webp", byte_size=100, width=100, height=80, sha256="b" * 64, uploaded_by=owner)
    payload = {
        "key": "main", "hero_eyebrow": "Selección editorial", "hero_title": "Un hogar claro",
        "editorial_title": "Historia", "editorial_body": "Contenido", "editorial_media": str(media.id),
        "hero_slides": [{"listing": str(catalog["listing"].id), "eyebrow_override": "Tecámac", "title_override": "Casa seleccionada", "subtitle_override": "Texto del slide", "sort_order": 3, "is_active": True}],
    }
    created = admin_client.post("/api/v1/admin/content/", payload, format="json")
    assert created.status_code == 201, created.data
    home = HomeContent.objects.get(key="main")
    slide = HomeHeroSlide.objects.get(home_content=home)
    assert slide.title_override == "Casa seleccionada" and slide.sort_order == 3
    public = admin_client.get("/api/v1/public/home/")
    assert public.status_code == 200
    assert public.data["content"]["hero_title"] == "Un hogar claro"
    assert public.data["content"]["editorial_media_url"].endswith("home/editorial.webp")
    assert public.data["hero"][0]["titleOverride"] == "Casa seleccionada"


@pytest.mark.django_db
def test_guide_hero_media_is_writable_and_public_after_publish(admin_client, owner):
    media = MediaAsset.objects.create(storage_key="guides/hero.webp", media_type="IMAGE", original_filename="hero.webp", mime_type="image/webp", byte_size=100, width=100, height=80, sha256="c" * 64, uploaded_by=owner)
    created = admin_client.post("/api/v1/admin/guides/", {"slug": "guia-imagen", "title": "Guía con imagen", "excerpt": "", "content": "Texto", "category": "zonas", "hero_media": str(media.id), "published": False, "featured": False}, format="json")
    assert created.status_code == 201, created.data
    assert created.data["heroImage"].endswith("guides/hero.webp")
    assert admin_client.get("/api/v1/public/guides/guia-imagen/").status_code == 404
    published = admin_client.patch(f"/api/v1/admin/guides/{created.data['id']}/", {"published": True, "version": created.data["version"]}, format="json")
    assert published.status_code == 200
    assert admin_client.get("/api/v1/public/guides/guia-imagen/").data["heroImage"].endswith("guides/hero.webp")


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


@pytest.mark.django_db
def test_geo_catalog_admin_creates_dependent_options_and_deactivates_them(admin_client):
    state_response = admin_client.post(
        "/api/v1/admin/states/", {"name": "Estado prueba", "code": "TST", "is_active": True}, format="json"
    )
    assert state_response.status_code == 201, state_response.data
    municipality_response = admin_client.post(
        "/api/v1/admin/municipalities/",
        {"state": state_response.data["id"], "name": "Municipio prueba", "is_active": True},
        format="json",
    )
    assert municipality_response.status_code == 201, municipality_response.data
    locality_response = admin_client.post(
        "/api/v1/admin/localities/",
        {"municipality": municipality_response.data["id"], "name": "Localidad prueba", "is_active": True},
        format="json",
    )
    assert locality_response.status_code == 201, locality_response.data
    neighborhood_response = admin_client.post(
        "/api/v1/admin/neighborhoods/",
        {
            "municipality": municipality_response.data["id"],
            "locality": locality_response.data["id"],
            "name": "Colonia prueba",
            "postal_code": "01010",
            "is_active": True,
        },
        format="json",
    )
    assert neighborhood_response.status_code == 201, neighborhood_response.data
    listing = admin_client.get(f"/api/v1/admin/neighborhoods/?municipality={municipality_response.data['id']}")
    assert listing.status_code == 200
    assert listing.data["results"][0]["name"] == "Colonia prueba"
    deactivated = admin_client.delete(f"/api/v1/admin/neighborhoods/{neighborhood_response.data['id']}/")
    assert deactivated.status_code == 204
    assert Neighborhood.objects.get(pk=neighborhood_response.data["id"]).is_active is False
    reactivated = admin_client.patch(
        f"/api/v1/admin/neighborhoods/{neighborhood_response.data['id']}/",
        {"name": "Colonia corregida", "is_active": True}, format="json",
    )
    assert reactivated.status_code == 200, reactivated.data
    assert Neighborhood.objects.get(pk=neighborhood_response.data["id"]).name == "Colonia corregida"
    assert admin_client.delete(f"/api/v1/admin/neighborhoods/{neighborhood_response.data['id']}/").status_code == 204
    preview = admin_client.get(f"/api/v1/admin/neighborhoods/{neighborhood_response.data['id']}/delete-preview/")
    assert preview.status_code == 200 and preview.data["can_delete"] is True
    removed = admin_client.post(
        f"/api/v1/admin/neighborhoods/{neighborhood_response.data['id']}/hard-delete/",
        {"confirmation": "Colonia corregida", "reason": "Ubicación duplicada creada por error"},
        format="json",
    )
    assert removed.status_code == 204
    assert not Neighborhood.objects.filter(pk=neighborhood_response.data["id"]).exists()
