"""Cover generation.

Two paths:
* ``IMAGE_PROVIDER=openai_compatible`` - call the image API for real art.
* otherwise - a deterministic, text-overlay cover built with Pillow so the
  product still produces a usable, legible cover offline.

The title is always overlaid as text (never asked of the image model) so it
stays legible at thumbnail size.
"""

from __future__ import annotations

import io
import textwrap
import uuid

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.db.models import Asset, Book
from app.services.storage import get_storage

log = get_logger(__name__)

COVER_W, COVER_H = 1600, 2560  # 5:8, KDP-friendly aspect

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _hex_to_rgb(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    value = (value or "").lstrip("#")
    if len(value) == 6:
        try:
            return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return fallback
    return fallback


def _contrast(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (17, 24, 39) if luminance > 150 else (255, 255, 255)


def render_text_cover(
    title: str,
    subtitle: str | None,
    author: str | None,
    palette: dict[str, str],
) -> bytes:
    """Create a legible text-overlay cover."""
    background = _hex_to_rgb(palette.get("primary", "#1F2937"), (31, 41, 55))
    accent = _hex_to_rgb(palette.get("accent", "#F59E0B"), (245, 158, 11))
    text_color = _contrast(background)

    image = Image.new("RGB", (COVER_W, COVER_H), background)
    draw = ImageDraw.Draw(image)

    # Accent band
    draw.rectangle([0, 0, COVER_W, 36], fill=accent)
    draw.rectangle([0, COVER_H - 36, COVER_W, COVER_H], fill=accent)

    # Title (wrapped, large, high contrast)
    title_font = _font(150)
    max_chars = 18
    lines = textwrap.wrap(title, width=max_chars)[:4] or [title]
    line_height = 170
    total = line_height * len(lines)
    y = int(COVER_H * 0.28 - total / 2)
    for line in lines:
        width = draw.textlength(line, font=title_font)
        draw.text(((COVER_W - width) / 2, y), line, font=title_font, fill=text_color)
        y += line_height

    # Rule
    draw.rectangle([COVER_W * 0.2, y + 30, COVER_W * 0.8, y + 36], fill=accent)
    y += 90

    if subtitle:
        sub_font = _font(64)
        for line in textwrap.wrap(subtitle, width=30)[:3]:
            width = draw.textlength(line, font=sub_font)
            draw.text(((COVER_W - width) / 2, y), line, font=sub_font, fill=text_color)
            y += 84

    if author:
        author_font = _font(60)
        label = f"by {author}"
        width = draw.textlength(label, font=author_font)
        draw.text(
            ((COVER_W - width) / 2, int(COVER_H * 0.78)), label, font=author_font, fill=accent
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


async def generate_cover_image(
    prompt: str, palette: dict[str, str] | None = None
) -> tuple[bytes, str]:
    """Return ``(image_bytes, provider)`` using the configured image provider."""
    settings = get_settings()
    if not settings.images_enabled:
        return b"", "none"

    if settings.image_provider == "openai_compatible":
        return await _openai_image(prompt), settings.image_provider
    return b"", "none"


async def _openai_image(prompt: str) -> bytes:
    settings = get_settings()
    if not settings.image_api_key:
        raise ProviderError("IMAGE_API_KEY is not set.", code="image_not_configured")
    payload = {"model": settings.image_model, "prompt": prompt, "size": "1024x1536", "n": 1}
    headers = {"Authorization": f"Bearer {settings.image_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.image_base_url.rstrip('/')}/images/generations",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise ProviderError("Image provider request failed.", details={"reason": str(exc)}) from exc

    import base64

    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        async with httpx.AsyncClient(timeout=60.0) as client:
            image_response = await client.get(item["url"])
            image_response.raise_for_status()
            return image_response.content
    raise ProviderError("Image provider returned no image.")


async def generate_cover(
    db: AsyncSession,
    book: Book,
    *,
    prompt: str | None = None,
    palette: dict[str, str] | None = None,
    cover_prompt: str | None = None,
) -> Asset:
    """Generate (or regenerate) the cover and attach it to the book."""
    palette = palette or {"primary": "#1F2937", "accent": "#F59E0B"}
    used_prompt = prompt or cover_prompt or f"Book cover about {book.topic}"

    image_bytes, provider = await generate_cover_image(used_prompt, palette)
    if not image_bytes:
        image_bytes = render_text_cover(book.title, book.subtitle, book.author_name, palette)
        provider = "text-overlay"

    asset_id = uuid.uuid4()
    key = f"covers/{book.id}/{asset_id}.png"
    size = await get_storage().put_bytes(key, image_bytes, "image/png")

    asset = Asset(
        id=asset_id,
        book_id=book.id,
        user_id=book.user_id,
        kind="cover",
        storage_key=key,
        mime_type="image/png",
        size_bytes=size,
        width=COVER_W,
        height=COVER_H,
        prompt=used_prompt,
        alt_text=f"Cover for {book.title}",
        provider=provider,
    )
    db.add(asset)
    book.cover_asset_id = asset_id
    await db.flush()
    log.info("cover_generated", book_id=str(book.id), provider=provider)
    return asset


def asset_url(asset: Asset | None, *, expires_in: int | None = None) -> str | None:
    if asset is None:
        return None
    return get_storage().signed_url(
        asset.storage_key, expires_in=expires_in, filename=f"{asset.kind}.png"
    )
