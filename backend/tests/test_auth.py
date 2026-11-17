"""
Authentication API Tests for CookMe
Tests: Registration, Login, CORS, Token validation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Basic API health check"""
    
    def test_api_health(self):
        """Test API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "CookMe API is running" in data["message"]


class TestCORS:
    """CORS configuration tests - critical for Apple device compatibility"""
    
    def test_cors_preflight_register(self):
        """Test CORS preflight for register endpoint"""
        response = requests.options(
            f"{BASE_URL}/api/auth/register",
            headers={
                "Origin": "https://different-origin.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "POST" in response.headers.get("access-control-allow-methods", "")
    
    def test_cors_preflight_login(self):
        """Test CORS preflight for login endpoint"""
        response = requests.options(
            f"{BASE_URL}/api/auth/login",
            headers={
                "Origin": "https://apple-device.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestRegistration:
    """User registration tests"""
    
    def test_register_new_user(self):
        """Test successful user registration"""
        timestamp = int(time.time())
        test_email = f"TEST_register_{timestamp}@cookme.com"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test Register User",
                "email": test_email,
                "password": "TestPassword123!"
            },
            headers={
                "Content-Type": "application/json",
                "Origin": "https://pantry-pal-203.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == test_email
        assert user["name"] == "Test Register User"
        assert "user_id" in user
        assert user["email_verified"] == True  # Auto-verified
        
        # Verify no email verification needed
        assert data.get("needs_verification") == False
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        timestamp = int(time.time())
        test_email = f"TEST_duplicate_{timestamp}@cookme.com"
        
        # First registration
        response1 = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "First User",
                "email": test_email,
                "password": "TestPassword123!"
            }
        )
        assert response1.status_code == 200
        
        # Second registration with same email
        response2 = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Second User",
                "email": test_email,
                "password": "DifferentPassword123!"
            }
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already registered" in data.get("detail", "").lower()
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields"""
        # Missing password
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 422  # Validation error


class TestLogin:
    """User login tests"""
    
    @pytest.fixture(autouse=True)
    def setup_test_user(self):
        """Create a test user for login tests"""
        import random
        self.timestamp = int(time.time() * 1000) + random.randint(1, 99999)
        self.test_email = f"TEST_login_{self.timestamp}@cookme.com"
        self.test_password = "TestPassword123!"
        
        # Register user
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test Login User",
                "email": self.test_email,
                "password": self.test_password
            }
        )
        # Handle case where email might already exist
        if response.status_code == 400:
            # Try with different timestamp
            self.timestamp = int(time.time() * 1000) + random.randint(100000, 999999)
            self.test_email = f"TEST_login_{self.timestamp}@cookme.com"
            response = requests.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "name": "Test Login User",
                    "email": self.test_email,
                    "password": self.test_password
                }
            )
        assert response.status_code == 200
        self.user_data = response.json()
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_email,
                "password": self.test_password
            },
            headers={
                "Content-Type": "application/json",
                "Origin": "https://pantry-pal-203.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == self.test_email
        assert "user_id" in user
        assert "avatar" in user
    
    def test_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_email,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid" in data.get("detail", "").lower()
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "nonexistent@cookme.com",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 401


class TestTokenValidation:
    """JWT token validation tests"""
    
    @pytest.fixture(autouse=True)
    def setup_authenticated_user(self):
        """Create and login a test user"""
        import random
        self.timestamp = int(time.time() * 1000) + random.randint(1, 99999)
        self.test_email = f"TEST_token_{self.timestamp}@cookme.com"
        
        # Register user
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test Token User",
                "email": self.test_email,
                "password": "TestPassword123!"
            }
        )
        # Handle case where email might already exist
        if response.status_code == 400:
            # Try with different timestamp
            self.timestamp = int(time.time() * 1000) + random.randint(100000, 999999)
            self.test_email = f"TEST_token_{self.timestamp}@cookme.com"
            response = requests.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "name": "Test Token User",
                    "email": self.test_email,
                    "password": "TestPassword123!"
                }
            )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
    
    def test_get_current_user(self):
        """Test /auth/me endpoint with valid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={
                "Authorization": f"Bearer {self.token}"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == self.test_email
        assert "user_id" in data
    
    def test_get_current_user_invalid_token(self):
        """Test /auth/me endpoint with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={
                "Authorization": "Bearer invalid_token_here"
            }
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_no_token(self):
        """Test /auth/me endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401


class TestLogout:
    """Logout functionality tests"""
    
    def test_logout(self):
        """Test logout endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data.get("message", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
