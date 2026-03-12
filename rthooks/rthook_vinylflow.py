"""
PyInstaller runtime hook for VinylFlow.

Runs before any application code and configures the environment for
bundled dependencies:
  - Points requests/urllib3 at the bundled certifi CA certificate bundle (SSL)
"""

import os
import sys

if hasattr(sys, "_MEIPASS"):
    meipass = sys._MEIPASS

    # certifi / requests
    # PyInstaller does not copy certifi's cacert.pem automatically.
    # Without it, every HTTPS request (Discogs API, cover art, etc.) raises
    # SSLCertVerificationError / CERTIFICATE_VERIFY_FAILED.
    cacert_path = os.path.join(meipass, "certifi", "cacert.pem")
    if os.path.exists(cacert_path):
        os.environ.setdefault("SSL_CERT_FILE", cacert_path)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", cacert_path)
