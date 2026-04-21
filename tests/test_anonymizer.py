"""
Tests for Anonymizer
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from openclaw_swarm.anonymizer import (
    Anonymizer, 
    PIIEntity, 
    anonymize, 
    de_anonymize, 
    check_pii
)


class TestAnonymizer:
    """Test Anonymizer system"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_anonymizer_init(self):
        """Test anonymizer initialization"""
        anon = Anonymizer()
        assert anon.patterns is not None
        assert len(anon.patterns) > 0
    
    def test_detect_email(self):
        """Test email detection"""
        anon = Anonymizer()
        
        text = "Contact us at support@example.com for help"
        entities = anon.detect_pii(text)
        
        assert len(entities) >= 1
        assert any(e.type == "email" for e in entities)
    
    def test_detect_ip_address(self):
        """Test IP address detection"""
        anon = Anonymizer()
        
        text = "Server IP: 192.168.1.1 is down"
        entities = anon.detect_pii(text)
        
        assert len(entities) >= 1
        assert any(e.type == "ip_address" for e in entities)
    
    def test_detect_phone(self):
        """Test phone number detection"""
        anon = Anonymizer()
        
        text = "Call me at 555-123-4567"
        entities = anon.detect_pii(text)
        
        assert len(entities) >= 1
        assert any(e.type == "phone" for e in entities)
    
    def test_detect_api_key(self):
        """Test API key detection"""
        anon = Anonymizer()
        
        text = "API key: sk-abcdefghijklmnopqrstuvwx"
        entities = anon.detect_pii(text)
        
        assert len(entities) >= 1
        assert any(e.type == "api_key" for e in entities)
    
    def test_anonymize_text(self):
        """Test text anonymization"""
        anon = Anonymizer()
        
        text = "Email: test@example.com, IP: 192.168.1.1"
        result = anon.anonymize(text)
        
        assert result.anonymized != text
        assert "<PII_EMAIL_" in result.anonymized
        assert "<PII_IP_ADDRESS_" in result.anonymized
        assert "test@example.com" not in result.anonymized
        assert "192.168.1.1" not in result.anonymized
        assert len(result.mapping) >= 2
    
    def test_de_anonymize_text(self):
        """Test text de-anonymization"""
        anon = Anonymizer()
        
        original = "Email: test@example.com"
        result = anon.anonymize(original)
        
        restored = anon.de_anonymize(result.anonymized, result.mapping)
        assert restored == original
    
    def test_multiple_same_type(self):
        """Test multiple PII of same type"""
        anon = Anonymizer()
        
        text = "Emails: a@example.com and b@example.com"
        result = anon.anonymize(text)
        
        assert len([k for k in result.mapping.keys() if "EMAIL" in k]) == 2
    
    def test_get_stats(self):
        """Test PII statistics"""
        anon = Anonymizer()
        
        text = "Email: a@example.com, IP: 1.2.3.4, IP: 5.6.7.8"
        stats = anon.get_stats(text)
        
        assert stats.get("email", 0) == 1
        assert stats.get("ip_address", 0) == 2
    
    def test_is_safe(self):
        """Test safety check"""
        anon = Anonymizer()
        
        safe_text = "This is a normal message"
        unsafe_text = "Contact: secret@example.com"
        
        assert anon.is_safe(safe_text) is True
        assert anon.is_safe(unsafe_text) is False
    
    def test_process_prompt(self):
        """Test prompt processing"""
        anon = Anonymizer()
        
        prompt = "Connect to server at 10.0.0.1"
        processed, mapping = anon.process_prompt(prompt)
        
        assert processed != prompt
        assert len(mapping) >= 1
    
    def test_process_response(self):
        """Test response processing"""
        anon = Anonymizer()
        
        prompt = "Server IP: 192.168.1.1"
        processed, mapping = anon.process_prompt(prompt)
        
        # Simulate LLM response with token
        response = f"Successfully connected to <PII_IP_ADDRESS_1>"
        restored = anon.process_response(response, mapping)
        
        assert "192.168.1.1" in restored
    
    def test_add_pattern(self):
        """Test adding custom pattern"""
        anon = Anonymizer()
        
        anon.add_pattern("custom_id", r'\bID-\d{5}\b')
        
        text = "User ID-12345 logged in"
        entities = anon.detect_pii(text)
        
        assert any(e.type == "custom_id" for e in entities)
    
    def test_remove_pattern(self):
        """Test removing pattern"""
        anon = Anonymizer()
        
        anon.remove_pattern("email")
        
        text = "Email: test@example.com"
        entities = anon.detect_pii(text)
        
        assert not any(e.type == "email" for e in entities)
    
    def test_anonymize_specific_types(self):
        """Test anonymizing specific types only"""
        anon = Anonymizer()
        
        text = "Email: a@example.com, IP: 1.2.3.4"
        result = anon.anonymize(text, types=["email"])
        
        assert "a@example.com" not in result.anonymized
        assert "1.2.3.4" in result.anonymized
        assert len(result.mapping) == 1
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        text = "Email: test@example.com"
        
        anon_text, mapping = anonymize(text)
        assert "test@example.com" not in anon_text
        
        restored = de_anonymize(anon_text, mapping)
        assert restored == text
        
        stats = check_pii(text)
        assert stats.get("email", 0) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])