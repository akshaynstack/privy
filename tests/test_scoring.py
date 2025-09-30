# tests/test_scoring.py  
"""Tests for fraud scoring service."""

import pytest
from app.services.scoring import compute_score, WEIGHTS


class TestRiskScoring:
    """Test cases for risk scoring algorithms."""
    
    def test_no_hits_returns_zero_score(self):
        """Test that no fraud indicators result in zero score."""
        score, level, reasons = compute_score([])
        
        assert score == 0
        assert level == "none"
        assert reasons == []
    
    def test_single_hit_scoring(self):
        """Test scoring with single fraud indicator."""
        hits = ["disposable_email"]
        score, level, reasons = compute_score(hits)
        
        assert score == WEIGHTS["disposable_email"]
        assert level == "medium"  # 70 should be medium (60-79)
        assert reasons == ["disposable_email"]
    
    def test_multiple_hits_scoring(self):
        """Test scoring with multiple fraud indicators."""
        hits = ["disposable_email", "vpn_ip"]
        score, level, reasons = compute_score(hits)
        
        expected_score = WEIGHTS["disposable_email"] + WEIGHTS["vpn_ip"]
        assert score == expected_score  # 70 + 60 = 130, capped at 100
        assert score <= 100  # Should be capped at 100
        assert level == "high"  # 100 should be high (80+)
        assert set(reasons) == set(hits)
    
    def test_unknown_hit_ignored(self):
        """Test that unknown fraud indicators are ignored."""
        hits = ["unknown_indicator", "disposable_email"]
        score, level, reasons = compute_score(hits)
        
        assert score == WEIGHTS["disposable_email"]
        assert "unknown_indicator" in reasons  # Should still be in reasons
        assert "disposable_email" in reasons
    
    def test_risk_level_boundaries(self):
        """Test risk level boundaries."""
        # Test "none" level (0-29)
        score, level, _ = compute_score([])
        assert level == "none"
        
        # Test "low" level (30-59) - need to mock a 30-point hit
        # Since we don't have one, we'll test with multiple_from_ip
        hits = ["multiple_from_ip"]  # 30 points
        score, level, _ = compute_score(hits)
        assert level == "low"
        assert score == 30
        
        # Test "medium" level (60-79)
        hits = ["vpn_ip"]  # 60 points
        score, level, _ = compute_score(hits)
        assert level == "medium"
        assert score == 60
        
        # Test "high" level (80+)
        hits = ["tor_exit"]  # 80 points
        score, level, _ = compute_score(hits)
        assert level == "high"
        assert score == 80
    
    def test_custom_blacklist_max_score(self):
        """Test that custom blacklist gives maximum score."""
        hits = ["custom_blacklist"]
        score, level, reasons = compute_score(hits)
        
        assert score == 100
        assert level == "high"
        assert reasons == ["custom_blacklist"]
    
    def test_score_capping(self):
        """Test that scores are capped at 100."""
        # Use multiple high-value indicators to exceed 100
        hits = ["custom_blacklist", "tor_exit", "disposable_email"]
        score, level, reasons = compute_score(hits)
        
        assert score == 100  # Should be capped
        assert level == "high"
        assert len(reasons) == 3
    
    @pytest.mark.parametrize("hits,expected_level", [
        ([], "none"),
        (["multiple_from_ip"], "low"),  # 30 points
        (["vpn_ip"], "medium"),  # 60 points  
        (["disposable_email"], "medium"),  # 70 points
        (["tor_exit"], "high"),  # 80 points
        (["custom_blacklist"], "high"),  # 100 points
    ])
    def test_risk_levels_parametrized(self, hits, expected_level):
        """Parametrized test for risk level classification."""
        _, level, _ = compute_score(hits)
        assert level == expected_level