import os
import base64
from io import BytesIO
from jinja2 import Template

PDF_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Satubumi Carbon Feasibility Assessment</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        body { 
            font-family: Helvetica, Arial, sans-serif; 
            color: #334155; 
            margin: 0; 
            padding: 0; 
            line-height: 1.5; 
            font-size: 11pt; 
        }
        
        /* HEADER (Kiri: Logo, Kanan: Dokumen Info) */
        .header-table { width: 100%; border-bottom: 2px solid #064e3b; padding-bottom: 15px; margin-bottom: 30px; }
        .header-table td { vertical-align: middle; }
        .header-left { text-align: left; width: 50%; }
        .header-right { text-align: right; width: 50%; font-size: 9pt; color: #64748b; line-height: 1.4; }
        
        /* 
         * PENYESUAIAN DIMENSI LOGO 
         * Rasio 1403 x 252 telah disesuaikan agar tidak gepeng di xhtml2pdf.
         * Lebar 250px dan Tinggi 45px sangat pas untuk margin A4.
         */
        .logo-img { 
            width: 250px; 
            height: 45px; 
        }
        
        .logo-text { font-size: 22pt; font-weight: 900; color: #064e3b; letter-spacing: 1px; margin: 0; }
        
        /* DOKUMEN TITLE & SCORE BOX */
        .title-section { width: 100%; margin-bottom: 40px; }
        .title-section td { vertical-align: top; }
        .doc-title { font-size: 18pt; font-weight: bold; color: #0f172a; margin: 0 0 5px 0; line-height: 1.2; }
        .doc-subtitle { font-size: 11pt; color: #10b981; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .score-box { 
            border: 1px solid #cbd5e1; 
            background-color: #f8fafc; 
            text-align: center; 
            padding: 15px; 
            width: 160px;
        }
        .score-label { font-size: 8pt; font-weight: bold; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .score-value { font-size: 26pt; font-weight: bold; margin: 0; line-height: 1; }
        .score-category { font-size: 9pt; font-weight: bold; margin-top: 5px; text-transform: uppercase; }
        
        /* Warna Skor Dinamis */
        .score-high .score-value { color: #059669; }
        .score-high .score-category { color: #059669; }
        .score-medium .score-value { color: #d97706; }
        .score-medium .score-category { color: #d97706; }
        .score-low .score-value { color: #dc2626; }
        .score-low .score-category { color: #dc2626; }

        /* TABEL DATA PROFESIONAL */
        .section-title { 
            font-size: 12pt; 
            font-weight: bold; 
            color: #064e3b; 
            margin-bottom: 10px; 
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 5px;
        }
        .data-table { width: 100%; border-collapse: collapse; margin-bottom: 35px; }
        .data-table th, .data-table td { padding: 10px 5px; text-align: left; }
        .data-table th { 
            font-size: 9pt; 
            color: #64748b; 
            text-transform: uppercase; 
            border-bottom: 1px solid #cbd5e1; 
            font-weight: bold;
        }
        .data-table td { 
            font-size: 10.5pt; 
            border-bottom: 1px solid #f1f5f9; 
            color: #1e293b;
        }
        .data-table td.val { text-align: right; font-weight: bold; font-family: 'Courier New', Courier, monospace; }
        
        /* Baris Sorotan (Highlight Row) */
        .row-highlight td { 
            background-color: #ecfdf5; 
            color: #064e3b; 
            font-weight: bold; 
            border-bottom: 1px solid #10b981; 
        }
        .row-highlight td.val { font-size: 11.5pt; color: #047857; }

        /* LIST REKOMENDASI */
        .rec-list { margin: 0; padding-left: 20px; color: #334155; }
        .rec-list li { margin-bottom: 8px; text-align: justify; }

        /* FOOTER */
        .footer { 
            margin-top: 40px; 
            font-size: 9pt; 
            color: #94a3b8; 
            text-align: center; 
            border-top: 1px solid #e2e8f0; 
            padding-top: 15px; 
        }

    </style>
</head>
<body>

    <!-- HEADER (Logo Kiri, Info Kanan) -->
    <table class="header-table">
        <tr>
            <td class="header-left">
                {% if logo_url %}
                    <img src="{{ logo_url }}" class="logo-img" alt="Satubumi Logo" />
                {% else %}
                    <h1 class="logo-text">SATUBUMI</h1>
                {% endif %}
            </td>
            <td class="header-right">
                <strong>RAPID-FS ENGINE</strong><br>
                Indicative Assessment Report<br>
                CONFIDENTIAL
            </td>
        </tr>
    </table>

    <!-- JUDUL & SKOR KELAYAKAN -->
    <table class="title-section">
        <tr>
            <td>
                <div class="doc-subtitle">Project Feasibility Analysis</div>
                <h2 class="doc-title">Carbon Project Indication<br>Assessment Report</h2>
                <div style="font-size: 10pt; color: #64748b; margin-top: 5px;">
                    Generated for: <strong>{{ location_name }}</strong>
                </div>
            </td>
            <td style="width: 170px; text-align: right;">
                <div class="score-box {% if score >= 81 %}score-high{% elif score >= 61 %}score-medium{% else %}score-low{% endif %}">
                    <div class="score-label">Feasibility Score</div>
                    <div class="score-value">{{ score }}</div>
                    <div class="score-category">{{ category }}</div>
                </div>
            </td>
        </tr>
    </table>

    <!-- 1. INFORMASI PROYEK -->
    <div class="section-title">1. Project Specifications</div>
    <table class="data-table">
        <tr>
            <td style="width: 30%; color: #64748b;">Project Location</td>
            <td style="width: 70%; font-weight: bold;">{{ location_name }}</td>
        </tr>
        <tr>
            <td style="color: #64748b;">Total Area Size</td>
            <td style="font-weight: bold;">{{ "{:,.2f}".format(area_ha) }} Hectares</td>
        </tr>
        <tr>
            <td style="color: #64748b;">Ecosystem Baseline</td>
            <td style="font-weight: bold;">{{ ecosystem_type | replace('_', ' ') | title }}</td>
        </tr>
        <tr>
            <td style="color: #64748b;">Project Crediting Period</td>
            <td style="font-weight: bold;">{{ project_duration_years }} Years</td>
        </tr>
        <tr>
            <td style="color: #64748b;">Assumed Carbon Price</td>
            <td style="font-weight: bold;">USD {{ "{:,.2f}".format(carbon_price_usd) }} / tCO2e</td>
        </tr>
    </table>

    <!-- 2. ESTIMASI KARBON -->
    <div class="section-title">2. Carbon Yield Projections</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Metric Indicator</th>
                <th style="text-align: right;">Estimated Volume</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Above-Ground Biomass (AGB)</td>
                <td class="val">{{ "{:,.2f}".format(agb_ton) }} Ton</td>
            </tr>
            <tr>
                <td>Carbon Stock Potential</td>
                <td class="val">{{ "{:,.2f}".format(carbon_stock_tc) }} tC</td>
            </tr>
            <tr>
                <td>CO2 Equivalent (CO2e) Conversion</td>
                <td class="val">{{ "{:,.2f}".format(co2e_ton) }} tCO2e</td>
            </tr>
            <tr>
                <td>Annual Emission Reduction (ER) Rate</td>
                <td class="val">{{ "{:,.2f}".format(annual_er) }} tCO2e / yr</td>
            </tr>
            <tr class="row-highlight">
                <td>Total Anticipated Carbon Credits (ACC)</td>
                <td class="val">{{ "{:,.2f}".format(acc_total_credits) }} tCO2e</td>
            </tr>
        </tbody>
    </table>

    <!-- 3. PROYEKSI KEUANGAN -->
    <div class="section-title">3. Financial Estimates (Indicative)</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Financial Component</th>
                <th style="text-align: right;">Projected Value (USD)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Gross Revenue <i>(Total ACC &times; Price)</i></td>
                <td class="val">$ {{ "{:,.2f}".format(gross_revenue_usd) }}</td>
            </tr>
            <tr>
                <td>Estimated Total Costs <i>(Dev, MRV, Opex)</i></td>
                <td class="val" style="color: #dc2626;">$ {{ "{:,.2f}".format(total_cost_usd) }}</td>
            </tr>
            <tr class="row-highlight">
                <td>Estimated Net Revenue</td>
                <td class="val">$ {{ "{:,.2f}".format(net_revenue_usd) }}</td>
            </tr>
        </tbody>
    </table>

    <!-- 4. REKOMENDASI STRATEGIS -->
    <div class="section-title">4. Strategic Recommendations</div>
    <ul class="rec-list">
        {% for rec in recommendations %}
            <li>{{ rec }}</li>
        {% endfor %}
    </ul>

    <div class="footer">
        Laporan ini dihasilkan secara otomatis oleh Satubumi Rapid-FS Engine sebagai studi awal indikatif (Initial Screening).<br/>
        <strong>Satubumi.org</strong> — Climate &amp; Sustainability Advisory Services.
    </div>
</body>
</html>
"""

def get_local_logo_base64() -> str:
    """
    Fungsi cerdas untuk mencari file 'logo.png' di folder yang sama
    dan mengubahnya menjadi format Base64 yang 100% terbaca oleh xhtml2pdf.
    """
    try:
        # Dapatkan path absolut dari folder tempat file ini berada (app/services/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "logo.png")
        
        # Baca gambar dan encode ke Base64
        with open(logo_path, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/png;base64,{b64_string}"
    except Exception:
        # Jika file logo.png tidak ditemukan, kembalikan string kosong
        # Script akan otomatis mundur (fallback) menggunakan Teks biasa "SATUBUMI"
        return ""

def generate_pdf_report(assessment_data: dict) -> bytes:
    
    # Ambil logo menggunakan Base64 anti-gagal
    LOGO_URL = get_local_logo_base64()
    
    template = Template(PDF_HTML_TEMPLATE)
    html_content = template.render(
        logo_url=LOGO_URL,
        location_name=assessment_data.get("location_name", "Undisclosed Location"),
        area_ha=float(assessment_data.get("area_ha") or 0),
        ecosystem_type=assessment_data.get("ecosystem_type", "Tropical Forest"),
        project_duration_years=assessment_data.get("project_duration_years", 30),
        carbon_price_usd=float(assessment_data.get("carbon_price_usd") or 10.0),
        score=assessment_data.get("feasibility_score", 0),
        category=assessment_data.get("feasibility_category", "N/A"),
        agb_ton=float(assessment_data.get("agb_ton") or 0),
        carbon_stock_tc=float(assessment_data.get("carbon_stock_tc") or 0),
        co2e_ton=float(assessment_data.get("co2e_ton") or 0),
        annual_er=float(assessment_data.get("annual_emission_reduction") or 0),
        acc_total_credits=float(assessment_data.get("acc_total_credits") or 0),
        gross_revenue_usd=float(assessment_data.get("gross_revenue_usd") or 0),
        total_cost_usd=float(
            assessment_data.get("total_cost_usd")
            or (assessment_data.get("cost_breakdown") or {}).get("total_cost_usd")
            or 0
        ),
        net_revenue_usd=float(assessment_data.get("net_revenue_usd") or 0),
        recommendations=assessment_data.get("recommendations") or [],
    )

    # 1) Coba WeasyPrint (Standar Emas)
    try:
        from weasyprint import HTML
        return HTML(string=html_content).write_pdf()
    except Exception:
        pass

    # 2) Fallback: xhtml2pdf (Aman)
    try:
        from xhtml2pdf import pisa
        buffer = BytesIO()
        result = pisa.CreatePDF(html_content, dest=buffer, encoding="utf-8")
        if result.err:
            raise RuntimeError("xhtml2pdf failed")
        return buffer.getvalue()
    except Exception as e:
        raise RuntimeError(
            f"Gagal membuat PDF. Pastikan xhtml2pdf terinstall (pip install xhtml2pdf). Detail: {e}"
        ) from e