"""Generate PDF + CSV reports for a sourcing job."""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from fpdf import FPDF

from ..models.schemas import SourcingJob


def _safe(text: str) -> str:
    """fpdf2 core fonts are Latin-1; strip unsupported chars."""
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf(job: SourcingJob) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=12, top=12, right=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _safe(f"Supplier Sourcing Report"), ln=True)
    pdf.cell(0, 10, _safe(f"Supplier Sourcing Report"), ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _safe(f"Product: {job.spec.product_name}"), ln=True)
    pdf.cell(0, 6, _safe(f"MOQ: {job.spec.moq}   Target: {job.spec.currency} {job.spec.target_price}"), ln=True)
    pdf.cell(0, 6, _safe(f"Ship to: {job.spec.ship_to_country}   Certs: {', '.join(job.spec.certifications) or 'None'}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _safe("Top Suppliers (Ranked)"), ln=True)
    pdf.set_font("Helvetica", "B", 9)
    headers = ["Rank", "Supplier", "Country", "Trust", "Quoted", "Landed", "MOQ", "Flags"]
    widths = [12, 52, 22, 14, 18, 18, 14, 35]
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, _safe(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for s in sorted(job.suppliers, key=lambda x: x.rank)[:10]:
        row = [
            str(s.rank),
            s.name[:30],
            s.country,
            f"{s.trust_score:.0f}",
            f"${s.quoted_price:.2f}",
            f"${s.landed_cost:.2f}",
            str(s.moq),
            (", ".join(s.red_flags)[:25] or "-"),
        ]
        for v, w in zip(row, widths):
            pdf.cell(w, 6, _safe(v), border=1)
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _safe("Negotiation Strategies & Inquiry Emails"), ln=True)
    pdf.set_font("Helvetica", "", 9)
    for s in sorted(job.suppliers, key=lambda x: x.rank)[:5]:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _safe(f"#{s.rank}  {s.name}  ({s.country})"), ln=True)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(w=0, h=5, text=_safe(f"Strategy: {s.negotiation_strategy or '-'}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        email_text = (s.inquiry_email or "[email not generated]").strip() or "-"
        pdf.multi_cell(w=0, h=5, text=_safe(email_text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out.encode("latin-1") if isinstance(out, str) else out


def build_csv(job: SourcingJob) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "rank", "supplier", "platform", "country", "years_active", "trust_score",
        "quoted_price", "landed_cost", "moq", "lead_time_days", "certifications",
        "red_flags", "compliance_ok", "contact_email", "profile_url",
    ])
    for s in sorted(job.suppliers, key=lambda x: x.rank):
        w.writerow([
            s.rank, s.name, s.platform, s.country, s.years_active, f"{s.trust_score:.1f}",
            f"{s.quoted_price:.2f}", f"{s.landed_cost:.2f}", s.moq, s.lead_time_days,
            "|".join(s.certifications), "|".join(s.red_flags), s.compliance_ok,
            s.contact_email, s.profile_url,
        ])
    return buf.getvalue().encode("utf-8")


def build_zip(job: SourcingJob) -> bytes:
    pdf_bytes = build_pdf(job)
    csv_bytes = build_csv(job)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.pdf", pdf_bytes)
        zf.writestr("suppliers.csv", csv_bytes)
        emails_dir = "inquiry_emails/"
        for s in sorted(job.suppliers, key=lambda x: x.rank)[:10]:
            safe_name = "".join(c for c in s.name if c.isalnum() or c in "._- ")[:40]
            zf.writestr(
                f"{emails_dir}{s.rank:02d}_{safe_name}.txt",
                f"To: {s.contact_email}\nSubject: Inquiry — {job.spec.product_name}\n\n{s.inquiry_email}\n\n--- Sample Request ---\n{s.sample_request}\n",
            )
    return buf.getvalue()
