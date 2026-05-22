"""Shared brand CSS + page chrome for proposal/audit PDFs."""
from __future__ import annotations

# Tokens mirror DESIGN.md
COLORS = {
    "oxblood": "#2A1414",
    "claret": "#6B2C2C",
    "brass": "#B08D57",
    "bone": "#FAF7F2",
    "cream": "#F1ECE3",
    "parchment": "#E2DACB",
    "espresso": "#1A1410",
    "ink": "#2B2620",
    "muted": "#6B655A",
    "champagne": "#E8D4A8",
}

BASE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..900;1,9..144,400..900&family=Inter:wght@300..700&family=JetBrains+Mono:wght@400;500&display=swap');

@page {{
  size: A4;
  margin: 18mm 18mm 18mm 18mm;
}}

* {{ box-sizing: border-box; }}
html, body {{
  font-family: "Inter", system-ui, sans-serif;
  color: {COLORS['ink']};
  background: {COLORS['bone']};
  line-height: 1.55;
  font-size: 10.5pt;
  margin: 0;
  padding: 0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}

h1, h2, h3 {{
  font-family: "Fraunces", Georgia, serif;
  color: {COLORS['espresso']};
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.15;
  margin: 0;
}}
h1 {{ font-size: 30pt; }}
h2 {{ font-size: 18pt; margin-top: 14pt; }}
h3 {{ font-size: 13pt; margin-top: 10pt; }}

.eyebrow {{
  font-family: "JetBrains Mono", monospace;
  font-size: 8pt;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: {COLORS['brass']};
  font-weight: 500;
}}

.muted {{ color: {COLORS['muted']}; }}
.brass {{ color: {COLORS['brass']}; }}
.oxblood {{ color: {COLORS['oxblood']}; }}
.tabular {{ font-family: "JetBrains Mono", monospace; font-feature-settings: "tnum"; }}

.brand-strip {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid {COLORS['parchment']};
  padding-bottom: 12pt;
  margin-bottom: 16pt;
}}
.brand-wordmark {{
  font-family: "Fraunces", serif;
  font-size: 22pt;
  letter-spacing: -0.02em;
  font-style: italic;
  color: {COLORS['espresso']};
  font-weight: 600;
}}
.brand-tagline {{
  font-family: "JetBrains Mono", monospace;
  font-size: 7.5pt;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: {COLORS['muted']};
  margin-top: 4pt;
}}
.brand-meta {{
  text-align: right;
  font-family: "JetBrains Mono", monospace;
  font-size: 8pt;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {COLORS['muted']};
}}

.hr-brass {{
  border: 0;
  border-top: 1px solid {COLORS['brass']};
  width: 60pt;
  margin: 12pt 0 14pt;
}}

.callout {{
  background: {COLORS['oxblood']};
  color: {COLORS['bone']};
  padding: 18pt 22pt;
  margin: 14pt 0;
}}
.callout .eyebrow {{ color: {COLORS['champagne']}; }}
.callout h2 {{ color: {COLORS['bone']}; }}

.callout-amount {{
  font-family: "Fraunces", serif;
  font-size: 38pt;
  line-height: 1.0;
  color: {COLORS['champagne']};
  letter-spacing: -0.02em;
  font-weight: 600;
  margin: 6pt 0 4pt;
}}

.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12pt; }}
.grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12pt; }}

table.calc {{
  width: 100%;
  border-collapse: collapse;
  margin: 8pt 0 14pt;
  font-size: 9pt;
}}
table.calc th, table.calc td {{
  border-bottom: 1px solid {COLORS['parchment']};
  padding: 6pt 8pt;
  text-align: left;
  vertical-align: top;
}}
table.calc th {{
  font-family: "JetBrains Mono", monospace;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 7.5pt;
  color: {COLORS['muted']};
  font-weight: 500;
  background: {COLORS['cream']};
}}
table.calc td.tabular {{ font-family: "JetBrains Mono", monospace; }}

.sev-critical {{ color: {COLORS['oxblood']}; font-weight: 600; }}
.sev-high {{ color: {COLORS['claret']}; font-weight: 600; }}
.sev-medium {{ color: {COLORS['brass']}; font-weight: 500; }}
.sev-low {{ color: {COLORS['muted']}; }}

.problem-card {{
  border-top: 1px solid {COLORS['parchment']};
  padding: 12pt 0;
}}
.problem-card .meta {{
  display: flex;
  gap: 12pt;
  margin-bottom: 4pt;
}}
.problem-card h3 {{ margin-top: 4pt; }}

.timeline-row {{
  display: grid;
  grid-template-columns: 60pt 1fr;
  gap: 10pt;
  padding: 6pt 0;
  border-bottom: 1px dotted {COLORS['parchment']};
}}
.timeline-row .week {{
  font-family: "JetBrains Mono", monospace;
  font-size: 8pt;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: {COLORS['brass']};
  padding-top: 2pt;
}}

.footer-pdf {{
  margin-top: 22pt;
  padding-top: 10pt;
  border-top: 1px solid {COLORS['parchment']};
  font-size: 8pt;
  color: {COLORS['muted']};
  display: flex;
  justify-content: space-between;
}}

.cta-pill {{
  display: inline-block;
  background: {COLORS['oxblood']};
  color: {COLORS['bone']};
  padding: 10pt 18pt;
  font-family: "JetBrains Mono", monospace;
  font-size: 8.5pt;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  text-decoration: none;
  border-radius: 2pt;
}}

.url-block {{
  font-family: "JetBrains Mono", monospace;
  font-size: 9pt;
  background: {COLORS['cream']};
  padding: 8pt 10pt;
  border: 1px solid {COLORS['parchment']};
  word-break: break-all;
}}

.kicker {{
  font-family: "Fraunces", serif;
  font-style: italic;
  font-size: 14pt;
  color: {COLORS['claret']};
  line-height: 1.35;
  margin: 8pt 0;
}}

ul.tight {{ margin: 6pt 0 10pt 18pt; padding: 0; }}
ul.tight li {{ margin-bottom: 4pt; }}
"""


def render_brand_strip(business: str, audit_date: str, doc_label: str) -> str:
    return f"""
    <div class="brand-strip">
      <div>
        <div class="brand-wordmark">Harsh Patadia</div>
        <div class="brand-tagline">Conversion-focused web systems · AI automation</div>
      </div>
      <div class="brand-meta">
        {doc_label}<br/>
        Prepared for {business}<br/>
        {audit_date}
      </div>
    </div>
    """
