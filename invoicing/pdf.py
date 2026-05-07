from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from PIL import Image, ImageDraw, ImageFont


PVL_LOGO_FILENAME = "PVL-LogoLockUp-4k_23aea92a-5a10-4e80-8421-66254bb1deb8.png"


def _safe_font(size=24):
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def render_invoice_pdf(invoice):
    width, height = 1240, 1754  # A4-ish canvas at screen density
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    text_font = _safe_font(24)
    title_font = _safe_font(40)
    small_font = _safe_font(20)
    bold_font = _safe_font(28)

    logo_path = Path(settings.BASE_DIR) / "public" / PVL_LOGO_FILENAME
    y = 40
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((360, 180))
        image.paste(logo, (60, y), logo)
    y += 160

    draw.text((60, y), "Provibe Life Invoice", fill="#0f172a", font=title_font)
    y += 70
    draw.text((60, y), f"Invoice: {invoice.invoice_number}", fill="#111827", font=bold_font)
    y += 40
    draw.text((60, y), f"Order: #{invoice.order_id}", fill="#111827", font=text_font)
    y += 35
    draw.text((60, y), f"Customer: {invoice.customer.name}", fill="#111827", font=text_font)
    y += 35
    draw.text((60, y), f"Status: {invoice.status}", fill="#111827", font=text_font)
    y += 35
    draw.text((60, y), f"Due Date: {invoice.due_date or '-'}", fill="#111827", font=text_font)
    y += 60

    draw.text((60, y), "Line Items", fill="#0f172a", font=bold_font)
    y += 45
    draw.line((60, y, width - 60, y), fill="#d1d5db", width=2)
    y += 18
    draw.text((60, y), "SKU", fill="#334155", font=small_font)
    draw.text((350, y), "Description", fill="#334155", font=small_font)
    draw.text((880, y), "Qty", fill="#334155", font=small_font)
    draw.text((960, y), "Amount", fill="#334155", font=small_font)
    y += 32
    draw.line((60, y, width - 60, y), fill="#e5e7eb", width=1)
    y += 12

    for item in invoice.order.items.select_related("product"):
        draw.text((60, y), item.product.sku, fill="#111827", font=small_font)
        draw.text((350, y), item.product.name[:45], fill="#111827", font=small_font)
        draw.text((880, y), str(item.quantity), fill="#111827", font=small_font)
        draw.text((960, y), f"${item.extended_price:.2f}", fill="#111827", font=small_font)
        y += 30

    if invoice.invoice_kind != "PRIMARY":
        y += 10
        draw.text((60, y), f"Adjustment Type: {invoice.invoice_kind}", fill="#7c2d12", font=small_font)
        y += 30

    y = max(y + 20, 1250)
    draw.line((60, y, width - 60, y), fill="#d1d5db", width=2)
    y += 20
    draw.text((760, y), "Subtotal:", fill="#111827", font=text_font)
    draw.text((980, y), f"${invoice.subtotal:.2f}", fill="#111827", font=text_font)
    y += 34
    draw.text((760, y), "Shipping:", fill="#111827", font=text_font)
    draw.text((980, y), f"${invoice.shipping_total:.2f}", fill="#111827", font=text_font)
    y += 34
    draw.text((760, y), "Tax:", fill="#111827", font=text_font)
    draw.text((980, y), f"${invoice.tax_total:.2f}", fill="#111827", font=text_font)
    y += 40
    draw.text((760, y), "Total:", fill="#0f172a", font=bold_font)
    draw.text((980, y), f"${invoice.total:.2f}", fill="#0f172a", font=bold_font)
    y += 70
    draw.text((60, y), "Payment: Use the hosted invoice link in the portal to pay online.", fill="#374151", font=small_font)

    buffer = BytesIO()
    image.save(buffer, format="PDF", resolution=100.0)
    buffer.seek(0)
    filename = f"{invoice.invoice_number}.pdf"
    invoice.pdf_file.save(filename, ContentFile(buffer.read()), save=True)
    return invoice
