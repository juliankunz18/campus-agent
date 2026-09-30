# 14. Certificates as PDF from Jinja2 and WeasyPrint

Date: 2026-09-30 · Status: Accepted

## Context

Engagement certificates must contain only verified facts. The board should be able to
adapt the layout (logo, text, signature) without programming.

## Decision

Certificates are rendered from an HTML template with Jinja2 and converted to PDF with
WeasyPrint when the board approves the application. Only data from the approved
application reaches the template; the model never writes certificate content. Each
group can replace the built-in template (`modules.certificates.template`); numbers
follow a configurable format such as `{year}-{seq:03d}`.

## Consequences

* WeasyPrint needs system libraries (Pango); it is added together with the PDF
  implementation and installed in the MCP server image.
