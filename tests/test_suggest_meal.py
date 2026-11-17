"""
Test suite for Suggest a Meal feature in CookMe app
Tests the /api/pantry/suggest-meal endpoint and related pantry functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = {
    "email": "chef@cookme.com",
    "password": "chef123"
}


class TestAuthentication:
    """Authentication tests for getting JWT token"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data or "token" in data, "No token in response"
        return data.get("access_token") or data.get("token")


class TestPantryEndpoints:
    """Test pantry CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token") or data.get("token")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        else:
            pytest.skip("Authentication failed")
    
    def test_get_pantry_items(self):
        """Test fetching pantry items"""
        response = requests.get(f"{BASE_URL}/api/pantry", headers=self.headers)
        assert response.status_code == 200, f"Failed to get pantry: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Pantry should return a list"
        print(f"Found {len(data)} pantry items")
        
        # Verify pantry has items (as mentioned in context)
        if len(data) > 0:
            item = data[0]
            assert "name" in item, "Pantry item should have name"
            assert "item_id" in item, "Pantry item should have item_id"
    
    def test_add_pantry_item(self):
        """Test adding a new pantry item"""
        test_item = {
            "name": "TEST_Tomatoes",
            "category": "Produce",
            "amount": "3 piece",
            "in_stock": True
        }
        
        response = requests.post(f"{BASE_URL}/api/pantry", json=test_item, headers=self.headers)
        assert response.status_code == 200, f"Failed to add item: {response.text}"
        
        data = response.json()
        assert data["name"] == test_item["name"], "Item name mismatch"
        assert "item_id" in data, "No item_id returned"
        
        # Cleanup - delete the test item
        item_id = data["item_id"]
        requests.delete(f"{BASE_URL}/api/pantry/{item_id}", headers=self.headers)


class TestSuggestMealEndpoint:
    """Test the Suggest a Meal feature endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token") or data.get("token")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        else:
            pytest.skip("Authentication failed")
    
    def test_suggest_meal_all_match(self):
        """Test suggest meal with 'all' match type"""
        payload = {
            "match_type": "all",
            "extra_ingredients": 0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json=payload,
            headers=self.headers,
            timeout=60  # AI calls can take time
        )
        
        assert response.status_code == 200, f"Suggest meal failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "pantry_items" in data, "Response should contain pantry_items"
        assert "saved_recipe_matches" in data, "Response should contain saved_recipe_matches"
        assert "ai_suggestions" in data, "Response should contain ai_suggestions"
        assert "match_criteria" in data, "Response should contain match_criteria"
        
        # Verify match criteria
        assert data["match_criteria"]["type"] == "all"
        assert data["match_criteria"]["extra_ingredients_allowed"] == 0
        
        print(f"Pantry items used: {data['pantry_items']}")
        print(f"Saved recipe matches: {len(data['saved_recipe_matches'])}")
        print(f"AI suggestions: {len(data['ai_suggestions'])}")
    
    def test_suggest_meal_most_match(self):
        """Test suggest meal with 'most' match type (70%+)"""
        payload = {
            "match_type": "most",
            "extra_ingredients": 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json=payload,
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Suggest meal failed: {response.text}"
        
        data = response.json()
        assert data["match_criteria"]["type"] == "most"
        assert data["match_criteria"]["extra_ingredients_allowed"] == 2
    
    def test_suggest_meal_some_match(self):
        """Test suggest meal with 'some' match type (any match)"""
        payload = {
            "match_type": "some",
            "extra_ingredients": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json=payload,
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Suggest meal failed: {response.text}"
        
        data = response.json()
        assert data["match_criteria"]["type"] == "some"
    
    def test_suggest_meal_ai_suggestions_structure(self):
        """Test that AI suggestions have correct structure"""
        payload = {
            "match_type": "most",
            "extra_ingredients": 3
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json=payload,
            headers=self.headers,
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["ai_suggestions"]:
            suggestion = data["ai_suggestions"][0]
            
            # Verify AI suggestion structure
            assert "title" in suggestion, "AI suggestion should have title"
            assert "description" in suggestion, "AI suggestion should have description"
            assert "source" in suggestion, "AI suggestion should have source"
            assert suggestion["source"] == "ai", "Source should be 'ai'"
            
            # Optional but expected fields
            expected_fields = ["prep_time", "cook_time", "difficulty", "servings", 
                             "matched_ingredients", "additional_ingredients_needed"]
            for field in expected_fields:
                if field in suggestion:
                    print(f"AI suggestion has {field}: {suggestion[field]}")
    
    def test_suggest_meal_extra_ingredients_range(self):
        """Test extra ingredients slider range (0-10)"""
        # Test minimum
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json={"match_type": "all", "extra_ingredients": 0},
            headers=self.headers,
            timeout=60
        )
        assert response.status_code == 200
        
        # Test maximum
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json={"match_type": "all", "extra_ingredients": 10},
            headers=self.headers,
            timeout=60
        )
        assert response.status_code == 200
    
    def test_suggest_meal_unauthorized(self):
        """Test suggest meal without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/pantry/suggest-meal",
            json={"match_type": "all", "extra_ingredients": 0}
        )
        assert response.status_code in [401, 403], "Should require authentication"


class TestSaveAiSuggestion:
    """Test saving AI suggestions as recipes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token") or data.get("token")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        else:
            pytest.skip("Authentication failed")
    
    def test_save_recipe_from_ai_suggestion(self):
        """Test saving an AI-generated recipe to user's collection"""
        # Create a recipe similar to what AI would suggest
        test_recipe = {
            "title": "TEST_AI_Suggested_Recipe",
            "description": "A test recipe from AI suggestion",
            "prep_time": "15 min",
            "cook_time": "30 min",
            "servings": 4,
            "difficulty": "Medium",
            "ingredients": [
                {"item": "Chicken Breast", "amount": "500g"},
                {"item": "Rice", "amount": "2 cups"}
            ],
            "steps": ["Step 1", "Step 2", "Step 3"],
            "tags": ["AI Suggested", "Pantry Recipe"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/recipes",
            json=test_recipe,
            headers=self.headers
        )
        
        assert response.status_code in [200, 201], f"Failed to save recipe: {response.text}"
        
        data = response.json()
        assert "recipe_id" in data, "Saved recipe should have recipe_id"
        assert data["title"] == test_recipe["title"]
        
        # Cleanup - delete the test recipe
        recipe_id = data["recipe_id"]
        requests.delete(f"{BASE_URL}/api/recipes/{recipe_id}", headers=self.headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
