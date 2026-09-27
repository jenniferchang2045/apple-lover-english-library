from __future__ import annotations

import pytest

from apple_lover_library.enums import RightsBasis
from apple_lover_library.errors import RightsGateError
from apple_lover_library.models import require_downloadable, require_importable


def test_only_public_domain_can_download() -> None:
    require_downloadable(RightsBasis.PUBLIC_DOMAIN)
    for basis in (RightsBasis.LICENSED, RightsBasis.UNKNOWN, RightsBasis.ORIGINAL):
        with pytest.raises(RightsGateError):
            require_downloadable(basis)


def test_import_allows_owned_or_public_not_unknown() -> None:
    require_importable(RightsBasis.LICENSED)
    require_importable(RightsBasis.PUBLIC_DOMAIN)
    with pytest.raises(RightsGateError):
        require_importable(RightsBasis.UNKNOWN)
    with pytest.raises(RightsGateError):
        require_importable(RightsBasis.ORIGINAL)
