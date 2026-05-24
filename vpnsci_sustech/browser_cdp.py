"""Browser/CDP helper gates for Phase 2 PDF fallbacks."""


def supports_browser_pdf_capture(url: str) -> bool:
    lowered = url.lower()
    return any(
        domain in lowered
        for domain in [
            "sciencedirect.com",
            "elsevier.com",
            "sciencedirectassets.com",
            "link.springer.com",
            "springer.com",
            "nature.com",
            "onlinelibrary.wiley.com",
            "wiley.com",
        ]
    )


def should_capture_pdf_response(url: str, mime_type: str) -> bool:
    lowered_url = (url or "").lower()
    lowered_mime = (mime_type or "").lower()
    if "pdf" not in lowered_mime:
        return False
    if (
        ".pdf" not in lowered_url
        and "/doi/pdf/" not in lowered_url
        and "pdfdirect" not in lowered_url
        and "pdfft" not in lowered_url
        and "sciencedirectassets.com" not in lowered_url
    ):
        return False
    return supports_browser_pdf_capture(lowered_url)
