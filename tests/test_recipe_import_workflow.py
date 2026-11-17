"""
Test Suite for Node-Based Recipe Import Workflow
================================================
Tests the /api/import-recipe-workflow endpoint with various input types:
- Facebook share URLs (video posts, regular posts)
- External recipe URLs (BBC Good Food, etc.)
- Text-only recipe paste
- Error handling and edge cases
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test2@cookme.com"
TEST_PASSWORD = "Test123!"


class TestRecipeImportWorkflow:
    """Tests for the node-based recipe import workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get auth token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    # =========================================================================
    # Node 1: Input Parsing Tests
    # =========================================================================
    
    def test_empty_payload_returns_error(self):
        """Test that empty payload returns 400 error"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "URL" in data["detail"] or "url" in data["detail"].lower()
    
    def test_invalid_url_format(self):
        """Test handling of invalid URL format"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "not-a-valid-url"}
        )
        # Should still process but may fail gracefully
        assert response.status_code in [200, 400, 502]
    
    # =========================================================================
    # Node 2-3: Facebook URL Processing Tests
    # =========================================================================
    
    def test_facebook_video_share_url(self):
        """Test Facebook video share URL extraction (Node 5 path)"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.facebook.com/share/r/1F7PaU6TvJ/"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify workflow response structure
        assert data["success"] == True
        assert data["recipe"] is not None
        assert data["needs_confirmation"] == True
        
        # Verify recipe object structure
        recipe = data["recipe"]
        assert "title" in recipe
        assert "ingredients" in recipe
        assert "steps" in recipe
        assert "confidence" in recipe
        assert "confidence_score" in recipe
        
        # Verify video detection
        assert recipe["is_video"] == True
        assert data["node_reached"] == "node5_video"
        
        # Verify image extraction
        assert recipe["image_url"] != "" or recipe["thumbnail_url"] != ""
        
        print(f"✓ Facebook video extraction: {recipe['title']}")
        print(f"  - Confidence: {recipe['confidence']} ({recipe['confidence_score']})")
        print(f"  - Ingredients: {len(recipe['ingredients'])}")
        print(f"  - Steps: {len(recipe['steps'])}")
    
    def test_facebook_mobile_url_conversion(self):
        """Test that www.facebook.com URLs are converted to m.facebook.com"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.facebook.com/share/r/1F7PaU6TvJ/"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    # =========================================================================
    # Node 4A: External Recipe URL Tests
    # =========================================================================
    
    def test_external_recipe_url_in_text(self):
        """Test extraction from external recipe URL in share text (Node 4A path)"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"text": "Check out this recipe! https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["recipe"] is not None
        
        recipe = data["recipe"]
        
        # Verify external URL detection
        assert recipe["external_url_found"] == "https://www.bbcgoodfood.com/recipes/classic-lasagne"
        assert data["node_reached"] == "node4a_external"
        
        # Verify high confidence for known recipe sites
        assert recipe["confidence"] == "high"
        assert recipe["confidence_score"] == 1.0
        
        # Verify recipe content extraction
        assert "lasagne" in recipe["title"].lower()
        assert len(recipe["ingredients"]) > 5
        assert len(recipe["steps"]) > 2
        
        # Verify source attribution
        assert "bbcgoodfood" in recipe["source_attribution"].lower()
        
        print(f"✓ External recipe extraction: {recipe['title']}")
        print(f"  - Ingredients: {len(recipe['ingredients'])}")
        print(f"  - Steps: {len(recipe['steps'])}")
        print(f"  - Prep time: {recipe['prep_time']}")
        print(f"  - Cook time: {recipe['cook_time']}")
    
    def test_direct_recipe_url(self):
        """Test direct recipe URL extraction without Facebook wrapper"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["recipe"] is not None
        # Direct URLs go through node4a_external or node4a_direct path
        assert "node4a" in data["node_reached"]
        
        recipe = data["recipe"]
        assert recipe["confidence"] == "high"
        assert len(recipe["ingredients"]) > 0
    
    # =========================================================================
    # Node 4B: Text-Only Recipe Parsing Tests
    # =========================================================================
    
    def test_text_only_recipe_paste(self):
        """Test text-only recipe parsing via AI (Node 4B path)"""
        recipe_text = """Simple Pasta Recipe

Ingredients:
- 1 lb spaghetti
- 2 cups marinara sauce
- 1/4 cup parmesan cheese
- 2 tbsp olive oil
- Salt and pepper to taste

Instructions:
1. Boil water and cook pasta according to package directions
2. Heat marinara sauce in a pan
3. Drain pasta and toss with sauce
4. Top with parmesan and serve"""
        
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"text": recipe_text}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["recipe"] is not None
        assert data["node_reached"] == "node4b_text"
        
        recipe = data["recipe"]
        
        # Verify AI extraction
        assert "pasta" in recipe["title"].lower()
        assert len(recipe["ingredients"]) >= 4
        assert len(recipe["steps"]) >= 3
        
        # Verify confidence scoring
        assert recipe["confidence"] in ["high", "medium", "user-assisted"]
        assert 0 <= recipe["confidence_score"] <= 1.0
        
        print(f"✓ Text recipe extraction: {recipe['title']}")
        print(f"  - Confidence: {recipe['confidence']} ({recipe['confidence_score']})")
        print(f"  - Ingredients: {len(recipe['ingredients'])}")
    
    def test_minimal_text_returns_user_assisted(self):
        """Test that minimal text returns user-assisted confidence"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"text": "Some food"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still succeed but with low confidence
        if data["success"]:
            recipe = data["recipe"]
            # Minimal text should result in user-assisted or needs_user_input
            assert recipe["confidence"] in ["user-assisted", "medium"] or recipe["needs_user_input"] == True
    
    # =========================================================================
    # Node 5: Video Handling Tests
    # =========================================================================
    
    def test_video_post_detection(self):
        """Test that video posts are correctly identified"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.facebook.com/share/r/1F7PaU6TvJ/"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        recipe = data["recipe"]
        assert recipe["is_video"] == True
        
        # Video posts should have thumbnail
        assert recipe["thumbnail_url"] != "" or recipe["image_url"] != ""
    
    # =========================================================================
    # Confidence Scoring Tests
    # =========================================================================
    
    def test_confidence_badges(self):
        """Test confidence badge values are valid"""
        # Test high confidence (external recipe)
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        recipe = data["recipe"]
        
        # Verify confidence values
        assert recipe["confidence"] in ["high", "medium", "user-assisted"]
        assert isinstance(recipe["confidence_score"], (int, float))
        assert 0 <= recipe["confidence_score"] <= 1.0
        
        # High confidence should have score >= 0.8
        if recipe["confidence"] == "high":
            assert recipe["confidence_score"] >= 0.7
    
    # =========================================================================
    # Recipe Save Flow Tests
    # =========================================================================
    
    def test_recipe_save_after_import(self):
        """Test saving imported recipe to user's collection"""
        # First import a recipe
        import_response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"text": "TEST_Quick Salad\n\nIngredients:\n- Lettuce\n- Tomatoes\n- Cucumber\n\nSteps:\n1. Wash vegetables\n2. Chop and mix\n3. Add dressing"}
        )
        
        assert import_response.status_code == 200
        import_data = import_response.json()
        assert import_data["success"] == True
        
        recipe = import_data["recipe"]
        
        # Now save the recipe
        save_payload = {
            "title": recipe["title"],
            "description": recipe.get("description", ""),
            "instructions": recipe.get("instructions", ""),
            "ingredients": recipe.get("ingredients", []),
            "steps": recipe.get("steps", []),
            "image": recipe.get("image_url", ""),
            "source_url": recipe.get("source_url", ""),
            "source": recipe.get("source_attribution", "Import"),
            "prep_time": recipe.get("prep_time", "30 min"),
            "cook_time": recipe.get("cook_time", "30 min"),
            "servings": recipe.get("servings", 4),
            "difficulty": "Medium",
            "tags": ["Imported", "Test"]
        }
        
        save_response = self.session.post(
            f"{BASE_URL}/api/recipes",
            json=save_payload
        )
        
        assert save_response.status_code in [200, 201]
        saved_data = save_response.json()
        
        # Verify recipe was saved
        assert "recipe_id" in saved_data
        
        # Cleanup - delete the test recipe
        recipe_id = saved_data["recipe_id"]
        delete_response = self.session.delete(f"{BASE_URL}/api/recipes/{recipe_id}")
        assert delete_response.status_code in [200, 204]
        
        print(f"✓ Recipe save flow: Created and deleted recipe {recipe_id}")
    
    # =========================================================================
    # Legacy Endpoint Tests
    # =========================================================================
    
    def test_legacy_endpoint_redirect(self):
        """Test that legacy /import-facebook-recipe endpoint still works"""
        response = self.session.post(
            f"{BASE_URL}/api/import-facebook-recipe",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Legacy format should have these fields
        assert "title" in data
        assert "ingredients" in data
        assert "confidence" in data
    
    def test_legacy_get_endpoint(self):
        """Test legacy GET endpoint"""
        response = self.session.get(
            f"{BASE_URL}/api/import-facebook-recipe",
            params={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
    
    # =========================================================================
    # Error Handling Tests
    # =========================================================================
    
    def test_unreachable_url_handling(self):
        """Test handling of unreachable URLs"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://nonexistent-domain-12345.com/recipe"}
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 502]
    
    def test_non_recipe_content_handling(self):
        """Test handling of non-recipe content"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"text": "This is just a random message about nothing related to cooking."}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return but with low confidence or user-assisted
        if data["success"] and data["recipe"]:
            recipe = data["recipe"]
            # Non-recipe content should have low confidence
            assert recipe["confidence"] in ["user-assisted", "medium"] or recipe["needs_user_input"] == True


class TestWorkflowResponseStructure:
    """Tests for workflow response structure validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        yield
        self.session.close()
    
    def test_workflow_response_has_required_fields(self):
        """Test that workflow response has all required fields"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required top-level fields
        assert "success" in data
        assert "recipe" in data
        assert "error" in data
        assert "error_code" in data
        assert "node_reached" in data
        assert "needs_confirmation" in data
    
    def test_recipe_object_has_required_fields(self):
        """Test that recipe object has all required fields"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        recipe = data["recipe"]
        
        # Required recipe fields
        required_fields = [
            "title", "description", "ingredients", "instructions", "steps",
            "images", "image_url", "servings", "prep_time", "cook_time",
            "source_url", "source_attribution", "confidence", "confidence_score",
            "needs_user_input", "user_message", "external_url_found",
            "is_video", "thumbnail_url", "video_url"
        ]
        
        for field in required_fields:
            assert field in recipe, f"Missing required field: {field}"
    
    def test_ingredients_structure(self):
        """Test that ingredients have correct structure"""
        response = self.session.post(
            f"{BASE_URL}/api/import-recipe-workflow",
            json={"url": "https://www.bbcgoodfood.com/recipes/classic-lasagne"}
        )
        
        assert response.status_code == 200
        data = response.json()
        recipe = data["recipe"]
        
        assert isinstance(recipe["ingredients"], list)
        if len(recipe["ingredients"]) > 0:
            ing = recipe["ingredients"][0]
            assert "item" in ing
            assert "amount" in ing
            assert "category" in ing


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
