import uuid
from unittest.mock import patch

from app.services.escrow import _generate_memo


def test_generate_memo():
    # Mock uuid.uuid4 to ensure deterministic output
    with patch('uuid.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        memo = _generate_memo()
        assert memo == "GS-123456781234"
        assert len(memo) == len("GS-") + 12
        assert memo.startswith("GS-")
