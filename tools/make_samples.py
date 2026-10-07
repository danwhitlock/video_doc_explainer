"""Generate the synthetic customer documents (PDF) and their ground-truth JSON.

Everything here is fictional: brands, people, addresses, reference numbers.
Phone numbers use the Ofcom drama range (01632 960xxx).

Usage:  uv run --with reportlab python tools/make_samples.py
Outputs: packs/<pack>/samples/<id>.pdf and packs/<pack>/samples/ground_truth/<id>.json

The ground truth is for evaluation only. The pipeline must never read it.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
FOOTER = "FICTIONAL DOCUMENT CREATED FOR A SOFTWARE DEMONSTRATION. Not a real offer or medical letter."

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, textColor=colors.grey)


def money(x: float) -> str:
    return f"£{x:,.2f}"


def nice_date(d: date) -> str:
    return d.strftime("%-d %B %Y")


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def table(rows, widths, header=False):
    t = Table(rows, colWidths=widths)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
                  ("BACKGROUND", (0, 1), (0, -1), colors.white)]
    t.setStyle(TableStyle(style))
    return t


def build_pdf(path: Path, story, brand: str):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(18 * mm, A4[1] - 14 * mm, brand)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 10 * mm, FOOTER)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=22 * mm, bottomMargin=18 * mm, title=path.stem)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


# ---------------------------------------------------------------- mortgage

def payment(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 100 / 12
    return principal * r / (1 - (1 + r) ** -months)


def balance_after(principal: float, annual_rate: float, pmt: float, k: int) -> float:
    r = annual_rate / 100 / 12
    return principal * (1 + r) ** k - pmt * ((1 + r) ** k - 1) / r


MORTGAGE_CUSTOMERS = [
    dict(id="m-001", customer_name="Ms Priya Raman", ref="FBS-2026-104381",
         address="Flat 4, 18 Quarry Lane, Stonebridge, ST4 9QP", offer_date=date(2026, 9, 14),
         purpose="purchase (first-time buyer)", property_value=285000, base_loan=256500,
         term_years=30, rate=4.89, fixed_months=24, svr=7.49, fee=0, fee_added=False,
         erc=[2, 1], product="2 Year Fixed First Home 90%"),
    dict(id="m-002", customer_name="Mr Gareth Lloyd", ref="FBS-2026-104512",
         address="Ty Glas, 3 Heol yr Afon, Llanfernant, LF2 6RT", offer_date=date(2026, 9, 22),
         purpose="remortgage", property_value=420000, base_loan=210000,
         term_years=20, rate=4.19, fixed_months=60, svr=7.49, fee=999, fee_added=True,
         erc=[5, 4, 3, 2, 1], product="5 Year Fixed Remortgage 60%"),
    dict(id="m-003", customer_name="Mrs Sophie Clarke", ref="FBS-2026-104777",
         address="27 Orchard Rise, Hollins Cross, HX7 2LD", offer_date=date(2026, 10, 1),
         purpose="purchase (home mover)", property_value=350000, base_loan=297500,
         term_years=35, rate=5.09, fixed_months=24, svr=7.49, fee=1499, fee_added=False,
         erc=[3, 2], product="2 Year Fixed Mover 85%"),
]


def mortgage_truth(c: dict) -> dict:
    loan = c["base_loan"] + (c["fee"] if c["fee_added"] else 0)
    n = c["term_years"] * 12
    m1 = payment(loan, c["rate"], n)
    bal = balance_after(loan, c["rate"], m1, c["fixed_months"])
    m2 = payment(bal, c["svr"], n - c["fixed_months"])
    total = m1 * c["fixed_months"] + m2 * (n - c["fixed_months"]) + (0 if c["fee_added"] else c["fee"])
    first_payment = add_months(c["offer_date"].replace(day=1), 2)
    end_fixed = add_months(first_payment, c["fixed_months"]) - timedelta(days=1)
    return {
        "customer_name": c["customer_name"],
        "offer_reference": c["ref"],
        "offer_date": c["offer_date"].isoformat(),
        "offer_expiry_date": add_months(c["offer_date"], 6).isoformat(),
        "property_address": c["address"],
        "mortgage_purpose": c["purpose"],
        "product_name": c["product"],
        "repayment_type": "capital and interest",
        "property_value": c["property_value"],
        "loan_amount": round(loan, 2),
        "ltv_percent": round(loan / c["property_value"] * 100, 1),
        "term_years": c["term_years"],
        "initial_rate_percent": c["rate"],
        "initial_period_months": c["fixed_months"],
        "initial_period_end_date": end_fixed.isoformat(),
        "follow_on_rate_percent": c["svr"],
        "monthly_payment_initial": round(m1, 2),
        "monthly_payment_follow_on": round(m2, 2),
        "total_amount_repayable": round(total, 2),
        "product_fee": c["fee"],
        "product_fee_added_to_loan": c["fee_added"],
        "early_repayment_charges": [{"year": i + 1, "percent": p} for i, p in enumerate(c["erc"])],
        "overpayment_allowance_percent": 10,
        "contact_phone": "01632 960412",
    }


def mortgage_pdf(c: dict, t: dict, path: Path):
    s = []
    s.append(Paragraph(f"{t['customer_name']}<br/>{t['property_address'].replace(', ', '<br/>')}", BODY))
    s.append(Spacer(1, 6))
    s.append(Paragraph(f"Our reference: {t['offer_reference']}<br/>Date: {nice_date(c['offer_date'])}", BODY))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Mortgage Offer and Illustration", H1))
    s.append(Paragraph(
        f"Dear {t['customer_name']},<br/><br/>We are pleased to offer you a mortgage for the {t['mortgage_purpose']} "
        f"of the property shown above. Please read this document carefully. It sets out the key features of the "
        f"mortgage, what you will pay, and the conditions that apply. This offer is valid until "
        f"{nice_date(date.fromisoformat(t['offer_expiry_date']))}.", BODY))

    s.append(Paragraph("1. Key features", H2))
    s.append(table([
        ["Product", t["product_name"]],
        ["Amount of loan", money(t["loan_amount"]) + (" (includes product fee added to the loan)" if t["product_fee_added_to_loan"] else "")],
        ["Value of the property", money(t["property_value"])],
        ["Loan to value", f"{t['ltv_percent']}%"],
        ["Mortgage term", f"{t['term_years']} years"],
        ["Repayment method", "Capital and interest (repayment)"],
    ], [55 * mm, 115 * mm]))

    s.append(Paragraph("2. Interest rate", H2))
    s.append(Paragraph(
        f"Your mortgage starts on a fixed rate of <b>{t['initial_rate_percent']:.2f}%</b> for {t['initial_period_months']} months, "
        f"until {nice_date(date.fromisoformat(t['initial_period_end_date']))}. After that, it will move to our Standard Variable Rate (SVR), "
        f"currently <b>{t['follow_on_rate_percent']:.2f}%</b>, for the rest of the term. The SVR can go up or down at any time.", BODY))

    s.append(Paragraph("3. What you will need to pay", H2))
    s.append(table([
        ["Period", "Number of payments", "Monthly payment"],
        [f"Fixed rate at {t['initial_rate_percent']:.2f}%", str(t["initial_period_months"]), money(t["monthly_payment_initial"])],
        [f"SVR at {t['follow_on_rate_percent']:.2f}% (assumed unchanged)", str(t["term_years"] * 12 - t["initial_period_months"]), money(t["monthly_payment_follow_on"])],
    ], [80 * mm, 40 * mm, 50 * mm], header=True))
    s.append(Spacer(1, 4))
    s.append(Paragraph(f"The total amount you will have to repay, assuming rates do not change, is <b>{money(t['total_amount_repayable'])}</b>.", BODY))
    rise = payment(balance_after(t["loan_amount"], t["initial_rate_percent"], t["monthly_payment_initial"], t["initial_period_months"]),
                   t["follow_on_rate_percent"] + 1, t["term_years"] * 12 - t["initial_period_months"])
    s.append(Paragraph(
        f"<i>Illustration only:</i> if the SVR were 1% higher when your fixed rate ends, your monthly payment could rise to "
        f"about {money(rise)}. This is not a forecast.", BODY))

    s.append(Paragraph("4. Fees", H2))
    if t["product_fee"] == 0:
        fee_text = "There is no product fee for this mortgage."
    elif t["product_fee_added_to_loan"]:
        fee_text = f"A product fee of {money(t['product_fee'])} applies. You asked us to add it to your loan, so you will pay interest on it."
    else:
        fee_text = f"A product fee of {money(t['product_fee'])} applies. This is payable on completion and is not added to your loan."
    s.append(Paragraph(fee_text + " A valuation was carried out at no cost to you.", BODY))

    s.append(Paragraph("5. Overpayments and early repayment charges", H2))
    s.append(Paragraph(
        f"You can overpay up to {t['overpayment_allowance_percent']}% of the outstanding balance each year during the fixed-rate period "
        f"without a charge. If you pay more than this, or repay the mortgage in full during the fixed-rate period, an early repayment "
        f"charge (ERC) applies to the amount repaid:", BODY))
    s.append(Spacer(1, 4))
    rows = [["Period", "Early repayment charge"]] + [[f"Year {e['year']}", f"{e['percent']}% of the amount repaid"] for e in t["early_repayment_charges"]]
    rows.append(["After the fixed-rate period", "No charge"])
    s.append(table(rows, [60 * mm, 110 * mm], header=True))

    s.append(Paragraph("6. Your obligations", H2))
    s.append(Paragraph(
        "Your home may be repossessed if you do not keep up repayments on your mortgage. You must keep the property insured "
        "against fire and other risks for its full rebuilding cost. If you want to move home, this mortgage may be transferred "
        "to a new property, subject to our lending criteria at the time.", BODY))

    s.append(KeepTogether([Paragraph("7. Contact us", H2), Paragraph(
        f"If you have questions about this offer, call our mortgage team on {t['contact_phone']} (Monday to Friday, 8am to 8pm, "
        f"Saturday 9am to 1pm), quoting reference {t['offer_reference']}.<br/><br/>Yours sincerely,<br/><br/>Mortgage Underwriting Team<br/>Fernmoor Building Society", BODY)]))
    build_pdf(path, s, "Fernmoor Building Society")


# ---------------------------------------------------------------- healthcare

LETTER_DATE = date(2026, 10, 5)

HEALTH_PATIENTS = [
    dict(
        id="h-001",
        truth={
            "patient_name": "Mrs Margaret Hughes",
            "hospital_number": "BH-482917",
            "letter_date": LETTER_DATE.isoformat(),
            "procedure_name": "Cataract surgery (right eye)",
            "procedure_plain_english": "The cloudy lens in your right eye is removed and replaced with a clear artificial lens.",
            "appointment_date": "2026-11-12",
            "arrival_time": "08:30",
            "location": "Eye Day Unit, Level 1, Brackenridge Community Hospital",
            "anaesthetic_type": "local",
            "stay_type": "day case",
            "expected_duration_hours": 3,
            "last_food_time": None,
            "last_clear_fluids_time": None,
            "bowel_preparation_required": False,
            "medicine_instructions": [
                "Keep taking your usual medicines, including eye drops, unless told otherwise.",
                "If you take blood-thinning medicines, call the pre-assessment team. Do not stop them without advice.",
            ],
            "items_to_bring": ["A list of your medicines", "Your glasses", "Something to read"],
            "escort_required": True,
            "escort_hours": None,
            "no_driving_days": None,
            "driving_advice": "Do not drive until your eye doctor says your sight meets the legal standard.",
            "recovery_summary": "Most people notice clearer sight within a few days. Use your eye drops as shown for 4 weeks.",
            "warning_signs": ["Increasing pain in the eye", "Your sight gets worse", "Increasing redness or sticky discharge"],
            "contact_phone": "01632 960215",
            "out_of_hours_phone": "01632 960999",
        },
        food_text="You can eat and drink normally before your operation.",
    ),
    dict(
        id="h-002",
        truth={
            "patient_name": "Mr Imran Shah",
            "hospital_number": "BH-517302",
            "letter_date": LETTER_DATE.isoformat(),
            "procedure_name": "Colonoscopy",
            "procedure_plain_english": "A thin, flexible tube with a camera is used to look at the lining of your large bowel.",
            "appointment_date": "2026-11-04",
            "arrival_time": "13:00",
            "location": "Endoscopy Unit, Ground Floor, Brackenridge General Hospital",
            "anaesthetic_type": "sedation",
            "stay_type": "day case",
            "expected_duration_hours": 4,
            "last_food_time": "2026-11-03T09:00",
            "last_clear_fluids_time": "2026-11-04T11:00",
            "bowel_preparation_required": True,
            "medicine_instructions": [
                "Stop taking iron tablets 7 days before your appointment.",
                "If you take blood-thinning medicines or medicines for diabetes, call the pre-assessment team. Do not stop them without advice.",
            ],
            "items_to_bring": ["A list of your medicines", "A dressing gown and slippers", "Your bowel preparation instruction sheet"],
            "escort_required": True,
            "escort_hours": 24,
            "no_driving_days": 1,
            "driving_advice": "Do not drive, cycle or operate machinery for 24 hours after sedation.",
            "recovery_summary": "You may feel bloated for a few hours. Most people are back to normal the next day.",
            "warning_signs": ["Severe tummy pain", "Passing more than a small amount of blood", "A high temperature"],
            "contact_phone": "01632 960348",
            "out_of_hours_phone": "01632 960999",
        },
        food_text=("Follow a low-fibre diet for 2 days before your appointment. Have your last solid food by 9am on Tuesday 3 November 2026. "
                   "After that, take the bowel preparation as described on the separate sheet and drink clear fluids only. "
                   "You can keep drinking clear fluids (water, squash, black tea) until 11am on the day of your appointment."),
    ),
    dict(
        id="h-003",
        truth={
            "patient_name": "Ms Chloe Bennett",
            "hospital_number": "BH-603845",
            "letter_date": LETTER_DATE.isoformat(),
            "procedure_name": "Knee arthroscopy (left knee)",
            "procedure_plain_english": "Keyhole surgery: a small camera and instruments are passed through tiny cuts to look inside and repair your knee joint.",
            "appointment_date": "2026-11-19",
            "arrival_time": "07:00",
            "location": "Day Surgery Unit, Level 2, Brackenridge General Hospital",
            "anaesthetic_type": "general",
            "stay_type": "day case",
            "expected_duration_hours": 6,
            "last_food_time": "2026-11-19T02:00",
            "last_clear_fluids_time": "2026-11-19T06:00",
            "bowel_preparation_required": False,
            "medicine_instructions": [
                "Take your usual morning medicines with a small sip of water, unless told otherwise.",
                "If you take blood-thinning medicines, call the pre-assessment team. Do not stop them without advice.",
            ],
            "items_to_bring": ["A list of your medicines", "Loose shorts or trousers", "Flat, comfortable shoes"],
            "escort_required": True,
            "escort_hours": 24,
            "no_driving_days": None,
            "driving_advice": "Do not drive until you can do an emergency stop without pain. For most people this is 1 to 2 weeks.",
            "recovery_summary": "Keep your leg raised when resting. Most people return to desk work within 1 to 2 weeks.",
            "warning_signs": ["Increasing redness, heat or swelling around the knee", "A high temperature",
                              "Pain or swelling in your calf", "Call 999 if you have chest pain or sudden breathlessness"],
            "contact_phone": "01632 960577",
            "out_of_hours_phone": "01632 960999",
        },
        food_text=("Do not eat anything after 2am on the day of your operation. This includes chewing gum and sweets. "
                   "You can drink water only until 6am."),
    ),
]


def health_pdf(p: dict, path: Path):
    t = p["truth"]
    appt = date.fromisoformat(t["appointment_date"])
    s = []
    s.append(Paragraph(f"{t['patient_name']}<br/>Hospital number: {t['hospital_number']}", BODY))
    s.append(Spacer(1, 6))
    s.append(Paragraph(f"Date: {nice_date(LETTER_DATE)}", BODY))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Your procedure: appointment and preparation", H1))
    s.append(Paragraph(
        f"Dear {t['patient_name']},<br/><br/>You are booked for a <b>{t['procedure_name'].lower()}</b>. "
        f"{t['procedure_plain_english']} This letter tells you when and where to come, how to prepare, and what to expect afterwards. "
        f"Please read it carefully and keep it.", BODY))

    s.append(Paragraph("Your appointment", H2))
    anaesthetic = {"local": "Local anaesthetic (you will be awake; the area is numbed)",
                   "sedation": "Sedation (you will be relaxed and drowsy but not fully asleep)",
                   "general": "General anaesthetic (you will be asleep)"}[t["anaesthetic_type"]]
    s.append(table([
        ["Date", appt.strftime("%A %-d %B %Y")],
        ["Please arrive at", t["arrival_time"]],
        ["Where", t["location"]],
        ["Anaesthetic", anaesthetic],
        ["Type of stay", f"Day case: expect to be with us for about {t['expected_duration_hours']} hours"],
    ], [45 * mm, 125 * mm]))

    s.append(Paragraph("Eating and drinking", H2))
    s.append(Paragraph(p["food_text"], BODY))

    s.append(Paragraph("Your medicines", H2))
    for m in t["medicine_instructions"]:
        s.append(Paragraph(f"• {m}", BODY))

    s.append(Paragraph("What to bring", H2))
    for b in t["items_to_bring"]:
        s.append(Paragraph(f"• {b}", BODY))
    s.append(Paragraph("Please leave jewellery and valuables at home.", BODY))

    s.append(Paragraph("Going home", H2))
    if t["escort_hours"]:
        esc = f"You must arrange for a responsible adult to take you home and stay with you for {t['escort_hours']} hours."
    else:
        esc = "You will need someone to take you home, as you will not be able to drive."
    s.append(Paragraph(f"{esc} {t['driving_advice']}", BODY))
    s.append(Paragraph(t["recovery_summary"], BODY))

    s.append(Paragraph("When to get help", H2))
    s.append(Paragraph("Contact us straight away if you have any of the following:", BODY))
    for w in t["warning_signs"]:
        s.append(Paragraph(f"• {w}", BODY))

    s.append(KeepTogether([Paragraph("Contact us", H2), Paragraph(
        f"If you have questions, or need to change your appointment, call {t['contact_phone']} (Monday to Friday, 9am to 5pm). "
        f"Outside these hours, call {t['out_of_hours_phone']}. Please quote your hospital number.<br/><br/>"
        f"Yours sincerely,<br/><br/>Pre-assessment Team<br/>Brackenridge Health", BODY)]))
    s.append(Spacer(1, 8))
    s.append(Paragraph("If you need this letter in large print, another language or an audio format, please call us.", SMALL))
    build_pdf(path, s, "Brackenridge Health")


def main():
    for c in MORTGAGE_CUSTOMERS:
        t = mortgage_truth(c)
        out = ROOT / "packs/mortgage/samples"
        (out / "ground_truth").mkdir(parents=True, exist_ok=True)
        (out / "ground_truth" / f"{c['id']}.json").write_text(json.dumps(t, indent=2))
        mortgage_pdf(c, t, out / f"{c['id']}.pdf")
    for p in HEALTH_PATIENTS:
        out = ROOT / "packs/healthcare/samples"
        (out / "ground_truth").mkdir(parents=True, exist_ok=True)
        (out / "ground_truth" / f"{p['id']}.json").write_text(json.dumps(p["truth"], indent=2))
        health_pdf(p, out / f"{p['id']}.pdf")
    print("Samples written.")


if __name__ == "__main__":
    main()
