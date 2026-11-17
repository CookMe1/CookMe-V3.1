"""
Test Shopping List and Pantry User Isolation
Tests that each user has their own shopping list and pantry items.
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
USER1_EMAIL = "shoptest@cookme.com"
USER1_PASSWORD = "Test123!"
USER2_EMAIL = "shoptest2@cookme.com"
USER2_PASSWORD = "Test123!"


class TestUserAuthentication:
    """Test that both test users can authenticate"""
    
    def test_user1_login(self):
        """User 1 can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": USER1_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == USER1_EMAIL
        print(f"✓ User 1 login successful: {data['user']['user_id']}")
    
    def test_user2_login(self):
        """User 2 can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER2_EMAIL,
            "password": USER2_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == USER2_EMAIL
        print(f"✓ User 2 login successful: {data['user']['user_id']}")


@pytest.fixture
def user1_token():
    """Get auth token for User 1"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER1_EMAIL,
        "password": USER1_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("User 1 authentication failed")


@pytest.fixture
def user2_token():
    """Get auth token for User 2"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER2_EMAIL,
        "password": USER2_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("User 2 authentication failed")


class TestShoppingListCRUD:
    """Test Shopping List CRUD operations"""
    
    def test_get_shopping_list_requires_auth(self):
        """GET /api/shopping-list requires authentication"""
        response = requests.get(f"{BASE_URL}/api/shopping-list")
        assert response.status_code in [401, 403]
        print("✓ Shopping list requires authentication")
    
    def test_get_shopping_list_user1(self, user1_token):
        """User 1 can get their shopping list"""
        response = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ User 1 shopping list retrieved: {len(data.get('items', []))} items")
    
    def test_update_shopping_list_user1(self, user1_token):
        """User 1 can update their shopping list"""
        test_items = [
            {"item_id": f"test_{uuid.uuid4().hex[:8]}", "name": "TEST_User1_Apples", "amount": "5", "checked": False, "category": "Produce"},
            {"item_id": f"test_{uuid.uuid4().hex[:8]}", "name": "TEST_User1_Milk", "amount": "1", "checked": False, "category": "Dairy"}
        ]
        
        response = requests.put(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"items": test_items}
        )
        assert response.status_code == 200
        print("✓ User 1 shopping list updated")
        
        # Verify items were saved
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        item_names = [item.get("name") for item in data.get("items", [])]
        assert "TEST_User1_Apples" in item_names
        assert "TEST_User1_Milk" in item_names
        print("✓ User 1 items persisted correctly")
    
    def test_clear_shopping_list_user1(self, user1_token):
        """User 1 can clear their shopping list"""
        response = requests.delete(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        print("✓ User 1 shopping list cleared")
        
        # Verify list is empty
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert len(data.get("items", [])) == 0
        print("✓ User 1 shopping list is empty after clear")


class TestShoppingListUserIsolation:
    """Test that shopping lists are isolated between users"""
    
    def test_user_isolation_shopping_list(self, user1_token, user2_token):
        """User 1's shopping items should not appear for User 2"""
        
        # Step 1: Clear both users' shopping lists
        requests.delete(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        requests.delete(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        
        # Step 2: Add unique items for User 1
        user1_items = [
            {"item_id": f"u1_{uuid.uuid4().hex[:8]}", "name": "TEST_ISOLATION_User1_Bananas", "amount": "6", "checked": False, "category": "Produce"},
            {"item_id": f"u1_{uuid.uuid4().hex[:8]}", "name": "TEST_ISOLATION_User1_Bread", "amount": "1", "checked": False, "category": "Bakery"}
        ]
        response = requests.put(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"items": user1_items}
        )
        assert response.status_code == 200
        print("✓ User 1 items added")
        
        # Step 3: Add unique items for User 2
        user2_items = [
            {"item_id": f"u2_{uuid.uuid4().hex[:8]}", "name": "TEST_ISOLATION_User2_Oranges", "amount": "4", "checked": False, "category": "Produce"},
            {"item_id": f"u2_{uuid.uuid4().hex[:8]}", "name": "TEST_ISOLATION_User2_Cheese", "amount": "1", "checked": False, "category": "Dairy"}
        ]
        response = requests.put(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={"items": user2_items}
        )
        assert response.status_code == 200
        print("✓ User 2 items added")
        
        # Step 4: Verify User 1 only sees their items
        user1_list = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        user1_item_names = [item.get("name") for item in user1_list.get("items", [])]
        
        assert "TEST_ISOLATION_User1_Bananas" in user1_item_names
        assert "TEST_ISOLATION_User1_Bread" in user1_item_names
        assert "TEST_ISOLATION_User2_Oranges" not in user1_item_names
        assert "TEST_ISOLATION_User2_Cheese" not in user1_item_names
        print("✓ User 1 only sees their own items")
        
        # Step 5: Verify User 2 only sees their items
        user2_list = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user2_token}"}
        ).json()
        user2_item_names = [item.get("name") for item in user2_list.get("items", [])]
        
        assert "TEST_ISOLATION_User2_Oranges" in user2_item_names
        assert "TEST_ISOLATION_User2_Cheese" in user2_item_names
        assert "TEST_ISOLATION_User1_Bananas" not in user2_item_names
        assert "TEST_ISOLATION_User1_Bread" not in user2_item_names
        print("✓ User 2 only sees their own items")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user2_token}"})
        print("✓ Shopping list user isolation VERIFIED")


class TestPantryCRUD:
    """Test Pantry CRUD operations"""
    
    def test_get_pantry_requires_auth(self):
        """GET /api/pantry requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pantry")
        assert response.status_code in [401, 403]
        print("✓ Pantry requires authentication")
    
    def test_get_pantry_user1(self, user1_token):
        """User 1 can get their pantry"""
        response = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ User 1 pantry retrieved: {len(data)} items")
    
    def test_add_pantry_item_user1(self, user1_token):
        """User 1 can add a pantry item"""
        response = requests.post(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "name": "TEST_User1_Tomatoes",
                "category": "Produce",
                "amount": "5 pieces",
                "in_stock": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_User1_Tomatoes"
        assert "item_id" in data
        print(f"✓ User 1 pantry item added: {data['item_id']}")
        return data["item_id"]
    
    def test_update_pantry_item_user1(self, user1_token):
        """User 1 can update a pantry item"""
        # First add an item
        add_response = requests.post(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "name": "TEST_User1_UpdateTest",
                "category": "Produce",
                "amount": "1 piece",
                "in_stock": True
            }
        )
        assert add_response.status_code == 200
        item_id = add_response.json()["item_id"]
        
        # Update the item
        update_response = requests.put(
            f"{BASE_URL}/api/pantry/{item_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"amount": "10 pieces"}
        )
        assert update_response.status_code == 200
        print(f"✓ User 1 pantry item updated: {item_id}")
        
        # Verify update
        pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        updated_item = next((item for item in pantry if item["item_id"] == item_id), None)
        assert updated_item is not None
        assert updated_item["amount"] == "10 pieces"
        print("✓ User 1 pantry item update verified")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pantry/{item_id}", headers={"Authorization": f"Bearer {user1_token}"})
    
    def test_delete_pantry_item_user1(self, user1_token):
        """User 1 can delete a pantry item"""
        # First add an item
        add_response = requests.post(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "name": "TEST_User1_DeleteTest",
                "category": "Produce",
                "amount": "1 piece",
                "in_stock": True
            }
        )
        assert add_response.status_code == 200
        item_id = add_response.json()["item_id"]
        
        # Delete the item
        delete_response = requests.delete(
            f"{BASE_URL}/api/pantry/{item_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert delete_response.status_code == 200
        print(f"✓ User 1 pantry item deleted: {item_id}")
        
        # Verify deletion
        pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        deleted_item = next((item for item in pantry if item["item_id"] == item_id), None)
        assert deleted_item is None
        print("✓ User 1 pantry item deletion verified")


class TestPantryUserIsolation:
    """Test that pantry items are isolated between users"""
    
    def test_user_isolation_pantry(self, user1_token, user2_token):
        """User 1's pantry items should not appear for User 2"""
        
        # Step 1: Add unique item for User 1
        user1_add = requests.post(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "name": "TEST_ISOLATION_User1_Garlic",
                "category": "Produce",
                "amount": "3 cloves",
                "in_stock": True
            }
        )
        assert user1_add.status_code == 200
        user1_item_id = user1_add.json()["item_id"]
        print(f"✓ User 1 pantry item added: {user1_item_id}")
        
        # Step 2: Add unique item for User 2
        user2_add = requests.post(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={
                "name": "TEST_ISOLATION_User2_Onions",
                "category": "Produce",
                "amount": "2 pieces",
                "in_stock": True
            }
        )
        assert user2_add.status_code == 200
        user2_item_id = user2_add.json()["item_id"]
        print(f"✓ User 2 pantry item added: {user2_item_id}")
        
        # Step 3: Verify User 1 only sees their items
        user1_pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        user1_item_names = [item.get("name") for item in user1_pantry]
        
        assert "TEST_ISOLATION_User1_Garlic" in user1_item_names
        assert "TEST_ISOLATION_User2_Onions" not in user1_item_names
        print("✓ User 1 only sees their own pantry items")
        
        # Step 4: Verify User 2 only sees their items
        user2_pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user2_token}"}
        ).json()
        user2_item_names = [item.get("name") for item in user2_pantry]
        
        assert "TEST_ISOLATION_User2_Onions" in user2_item_names
        assert "TEST_ISOLATION_User1_Garlic" not in user2_item_names
        print("✓ User 2 only sees their own pantry items")
        
        # Step 5: Verify User 2 cannot delete User 1's item
        cross_delete = requests.delete(
            f"{BASE_URL}/api/pantry/{user1_item_id}",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert cross_delete.status_code == 404  # Should not find item
        print("✓ User 2 cannot delete User 1's pantry item")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pantry/{user1_item_id}", headers={"Authorization": f"Bearer {user1_token}"})
        requests.delete(f"{BASE_URL}/api/pantry/{user2_item_id}", headers={"Authorization": f"Bearer {user2_token}"})
        print("✓ Pantry user isolation VERIFIED")


class TestShoppingListAddItems:
    """Test the add-items endpoint for shopping list"""
    
    def test_add_items_endpoint(self, user1_token):
        """POST /api/shopping-list/add-items adds multiple items"""
        # Clear first
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})
        
        response = requests.post(
            f"{BASE_URL}/api/shopping-list/add-items",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"items": ["TEST_AddItems_Eggs", "TEST_AddItems_Butter", "TEST_AddItems_Sugar"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added_count"] == 3
        print(f"✓ Added {data['added_count']} items via add-items endpoint")
        
        # Verify items were added
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-list",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        items = get_response.json().get("items", [])
        item_names = [item.get("name") for item in items]
        assert "TEST_AddItems_Eggs" in item_names
        assert "TEST_AddItems_Butter" in item_names
        assert "TEST_AddItems_Sugar" in item_names
        print("✓ Items verified in shopping list")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})
    
    def test_add_items_skips_duplicates(self, user1_token):
        """POST /api/shopping-list/add-items skips existing items"""
        # Clear and add initial items
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})
        requests.post(
            f"{BASE_URL}/api/shopping-list/add-items",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"items": ["TEST_Duplicate_Flour"]}
        )
        
        # Try to add same item again
        response = requests.post(
            f"{BASE_URL}/api/shopping-list/add-items",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"items": ["TEST_Duplicate_Flour", "TEST_Duplicate_NewItem"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added_count"] == 1  # Only new item added
        assert data["skipped_count"] == 1  # Duplicate skipped
        print(f"✓ Duplicate handling: added={data['added_count']}, skipped={data['skipped_count']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, user1_token, user2_token):
        """Clean up all TEST_ prefixed items"""
        # Clean User 1 pantry
        user1_pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        for item in user1_pantry:
            if item.get("name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/pantry/{item['item_id']}",
                    headers={"Authorization": f"Bearer {user1_token}"}
                )
        
        # Clean User 2 pantry
        user2_pantry = requests.get(
            f"{BASE_URL}/api/pantry",
            headers={"Authorization": f"Bearer {user2_token}"}
        ).json()
        for item in user2_pantry:
            if item.get("name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/pantry/{item['item_id']}",
                    headers={"Authorization": f"Bearer {user2_token}"}
                )
        
        # Clear shopping lists
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user1_token}"})
        requests.delete(f"{BASE_URL}/api/shopping-list", headers={"Authorization": f"Bearer {user2_token}"})
        
        print("✓ Test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
