"""Tests for the Gemini image generation endpoint."""

import pytest

from app.services.gemini_image_service import GeminiImageGenerationError


@pytest.mark.asyncio
async def test_generate_image_route_returns_images(client, monkeypatch):
    async def fake_generate_image(**kwargs):
        return {
            "model": kwargs["model_id"],
            "prompt": kwargs["prompt"],
            "images": [{"data": "ZmFrZS1pbWFnZS1kYXRh", "mime_type": "image/png"}],
            "text": "ok",
        }

    monkeypatch.setattr("app.routers.image_generation.generate_image", fake_generate_image)

    resp = await client.post(
        "/image-generation/generate",
        json={
            "model": "nano-banana-2",
            "prompt": "A cinematic portrait of a robot chef",
            "aspect_ratio": "1:1",
            "quality": "1K",
            "images": [],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "nano-banana-2"
    assert data["prompt"] == "A cinematic portrait of a robot chef"
    assert data["images"][0]["mime_type"] == "image/png"
    assert data["images"][0]["data"] == "ZmFrZS1pbWFnZS1kYXRh"


@pytest.mark.asyncio
async def test_generate_image_route_returns_502_on_service_error(client, monkeypatch):
    async def fake_generate_image(**kwargs):
        raise GeminiImageGenerationError("boom")

    monkeypatch.setattr("app.routers.image_generation.generate_image", fake_generate_image)

    resp = await client.post(
        "/image-generation/generate",
        json={
            "model": "nano-banana-2",
            "prompt": "A cinematic portrait of a robot chef",
            "aspect_ratio": "1:1",
            "quality": "2K",
            "images": [],
        },
    )

    assert resp.status_code == 502
    assert resp.json()["detail"] == "boom"


@pytest.mark.asyncio
async def test_generate_image_route_rejects_pro_model_without_auth(client):
    resp = await client.post(
        "/image-generation/generate",
        json={
            "model": "nano-banana-pro",
            "prompt": "A cinematic portrait of a robot chef",
            "aspect_ratio": "1:1",
            "quality": "2K",
            "images": [],
        },
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Nano Banana Pro is available for Admin users only"


@pytest.mark.asyncio
async def test_generate_image_route_rejects_pro_model_for_non_admin(client, auth_headers):
    resp = await client.post(
        "/image-generation/generate",
        headers=auth_headers,
        json={
            "model": "nano-banana-pro",
            "prompt": "A cinematic portrait of a robot chef",
            "aspect_ratio": "1:1",
            "quality": "2K",
            "images": [],
        },
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Nano Banana Pro is available for Admin users only"


@pytest.mark.asyncio
async def test_generate_image_route_allows_pro_model_for_admin(client, admin_headers, monkeypatch):
    async def fake_generate_image(**kwargs):
        return {
            "model": kwargs["model_id"],
            "prompt": kwargs["prompt"],
            "images": [{"data": "ZmFrZS1pbWFnZS1kYXRh", "mime_type": "image/png"}],
            "text": "ok",
        }

    monkeypatch.setattr("app.routers.image_generation.generate_image", fake_generate_image)

    resp = await client.post(
        "/image-generation/generate",
        headers=admin_headers,
        json={
            "model": "nano-banana-pro",
            "prompt": "A cinematic portrait of a robot chef",
            "aspect_ratio": "1:1",
            "quality": "2K",
            "images": [],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "nano-banana-pro"