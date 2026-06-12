"""
Verifiers -- Layer 4: claims-vs-disk checks.

Where constraints.py validates JSON internal consistency (L1/L2/L3),
verifiers compare recon claims against the actual repository on disk.

Each modality is a separate module:
  - paths.py: filesystem existence of declared paths

All findings are advisory (WARN). They do not block the pipeline.
"""

from .paths import verify_recon_paths

__all__ = ["verify_recon_paths"]
