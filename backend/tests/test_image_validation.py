"""
Test Image Quality Validation Feature
Tests the /api/recipes/validate-image endpoint and related functionality
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "imagetest@cookme.com"
TEST_PASSWORD = "testpass123"


class TestImageValidation:
    """Tests for the image quality validation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_validate_image_endpoint_exists(self):
        """Test that the validate-image endpoint exists and requires auth"""
        # Test without auth
        response = requests.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={"image_data": "test"}
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_validate_image_requires_image_data(self):
        """Test that endpoint requires image_data parameter"""
        response = self.session.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={}
        )
        assert response.status_code == 400, f"Expected 400 for missing image_data, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "image" in data["detail"].lower() or "required" in data["detail"].lower()
    
    def test_validate_image_rejects_tiny_image(self):
        """Test that a 1x1 pixel image (too small/dark) is rejected"""
        # Create a 1x1 pixel black PNG (base64 encoded)
        # This is a minimal valid PNG that should be rejected as too dark/small
        tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={"image_data": f"data:image/png;base64,{tiny_png_base64}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should have status field
        assert "status" in data, "Response should have 'status' field"
        
        # Should be REJECT for tiny/dark image
        assert data["status"] == "REJECT", f"Expected REJECT for tiny image, got {data['status']}"
        
        # Should have a reason
        assert "reason" in data or data.get("reason") is not None, "REJECT should include a reason"
        print(f"Rejection reason: {data.get('reason')}")
    
    def test_validate_image_response_format(self):
        """Test that response has correct format (status: ACCEPT or REJECT)"""
        # Use a small but valid test image
        tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={"image_data": f"data:image/png;base64,{tiny_png_base64}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "status" in data, "Response must have 'status' field"
        assert data["status"] in ["ACCEPT", "REJECT"], f"Status must be ACCEPT or REJECT, got {data['status']}"
        
        # If REJECT, should have reason
        if data["status"] == "REJECT":
            assert "reason" in data, "REJECT response should have 'reason' field"
            assert data["reason"] is not None, "REJECT reason should not be None"
    
    def test_validate_image_handles_base64_without_prefix(self):
        """Test that endpoint handles base64 data without data URL prefix"""
        # Raw base64 without data:image/png;base64, prefix
        tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={"image_data": tiny_png_base64}
        )
        
        # Should handle gracefully (either 200 with result or appropriate error)
        assert response.status_code in [200, 400, 500], f"Unexpected status code: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_validate_image_with_data_url_prefix(self):
        """Test that endpoint correctly handles data URL format"""
        tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/recipes/validate-image",
            json={"image_data": f"data:image/png;base64,{tiny_png_base64}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"Response with data URL prefix: {data}")


class TestImageValidationIntegration:
    """Integration tests for image validation in recipe workflows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_analyze_photo_endpoint_exists(self):
        """Test that analyze-photo endpoint exists (used after validation)"""
        # This endpoint should exist and require auth
        response = requests.post(
            f"{BASE_URL}/api/recipes/analyze-photo",
            json={"image_data": "test"}
        )
        # Should return 401/403 without auth
        assert response.status_code in [401, 403]
    
    def test_analyze_photo_with_auth(self):
        """Test analyze-photo endpoint with authentication"""
        tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/recipes/analyze-photo",
            json={"image_data": f"data:image/png;base64,{tiny_png_base64}"}
        )
        
        # Should return 200 or 500 (if AI fails on tiny image)
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"


class TestRecipeEndpoints:
    """Test recipe endpoints that use image validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_get_recipes_list(self):
        """Test getting recipes list"""
        response = self.session.get(f"{BASE_URL}/api/recipes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_filter_options(self):
        """Test getting filter options"""
        response = self.session.get(f"{BASE_URL}/api/recipes/filters/options")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "cuisines" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
