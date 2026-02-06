"""
Tests for error_explanations module
"""
import pytest
from app.core.error_explanations import (
    ERROR_EXPLANATIONS,
    get_error_explanation,
    explain_seeding_with_revoked_rights,
)


class TestErrorExplanationsDict:
    """Tests for the ERROR_EXPLANATIONS dictionary"""

    def test_signature_invalide_entry(self):
        entry = ERROR_EXPLANATIONS["signature_invalide"]
        assert entry["category"] == "FILE_ERROR"
        assert "title" in entry
        assert "description" in entry
        assert isinstance(entry["solutions"], list)
        assert len(entry["solutions"]) > 0

    def test_droits_revoques_entry(self):
        entry = ERROR_EXPLANATIONS["droits_revoques"]
        assert entry["category"] == "ACCOUNT_ERROR"
        assert "note" in entry

    def test_not_authorized_entry(self):
        entry = ERROR_EXPLANATIONS["not_authorized"]
        assert entry["category"] == "CLIENT_ERROR"

    def test_torrent_not_found_entry(self):
        entry = ERROR_EXPLANATIONS["torrent_not_found"]
        assert entry["category"] == "TRACKER_ERROR"

    def test_all_entries_have_required_fields(self):
        for key, entry in ERROR_EXPLANATIONS.items():
            assert "title" in entry, f"Missing 'title' in {key}"
            assert "description" in entry, f"Missing 'description' in {key}"
            assert "solutions" in entry, f"Missing 'solutions' in {key}"
            assert "category" in entry, f"Missing 'category' in {key}"


class TestGetErrorExplanation:
    """Tests for get_error_explanation function"""

    def test_signature_invalide_match(self):
        result = get_error_explanation("La signature invalide du torrent")
        assert result["category"] == "FILE_ERROR"

    def test_droits_revoques_match(self):
        result = get_error_explanation("Vos droits de téléchargement sont révoqués")
        assert result["category"] == "ACCOUNT_ERROR"

    def test_not_authorized_match(self):
        result = get_error_explanation("Client not authorized on this tracker")
        assert result["category"] == "CLIENT_ERROR"

    def test_not_found_match(self):
        result = get_error_explanation("Torrent not found")
        assert result["category"] == "TRACKER_ERROR"

    def test_introuvable_match(self):
        result = get_error_explanation("Le torrent est introuvable")
        assert result["category"] == "TRACKER_ERROR"

    def test_unknown_error_fallback(self):
        result = get_error_explanation("Something completely unexpected happened")
        assert result["category"] == "UNKNOWN_ERROR"
        assert result["title"] == "Erreur inconnue"
        assert "Something completely unexpected happened" in result["description"]
        assert len(result["solutions"]) > 0


class TestExplainSeedingWithRevokedRights:
    """Tests for explain_seeding_with_revoked_rights function"""

    def test_returns_string(self):
        result = explain_seeding_with_revoked_rights()
        assert isinstance(result, str)

    def test_contains_relevant_info(self):
        result = explain_seeding_with_revoked_rights()
        assert "seeding" in result.lower() or "Seeding" in result
        assert "ratio" in result.lower()
        assert "tracker" in result.lower()
