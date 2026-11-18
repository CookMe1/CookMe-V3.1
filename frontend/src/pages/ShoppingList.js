import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, Check, Trash2, ShoppingCart, ShoppingBag, ArrowLeft, Loader2, RefreshCw, Mic, MicOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Supermarket aisle mapping for intelligent sorting
const AISLE_ORDER = {
  'Produce': { order: 1, aisle: 'Fresh Produce', icon: '🥬' },
  'Bakery': { order: 2, aisle: 'Bakery', icon: '🍞' },
  'Dairy': { order: 3, aisle: 'Dairy & Eggs', icon: '🥛' },
  'Meat': { order: 4, aisle: 'Meat & Seafood', icon: '🥩' },
  'Seafood': { order: 4, aisle: 'Meat & Seafood', icon: '🐟' },
  'Deli': { order: 5, aisle: 'Deli', icon: '🧀' },
  'Frozen': { order: 6, aisle: 'Frozen Foods', icon: '🧊' },
  'Pantry': { order: 7, aisle: 'Pantry & Dry Goods', icon: '🥫' },
  'Canned': { order: 7, aisle: 'Pantry & Dry Goods', icon: '🥫' },
  'Grains': { order: 7, aisle: 'Pantry & Dry Goods', icon: '🥫' },
  'Spices': { order: 8, aisle: 'Spices & Seasonings', icon: '🧂' },
  'Oils': { order: 9, aisle: 'Oils & Condiments', icon: '🫒' },
  'Condiments': { order: 9, aisle: 'Oils & Condiments', icon: '🫒' },
  'Baking': { order: 10, aisle: 'Baking Supplies', icon: '🎂' },
  'Beverages': { order: 11, aisle: 'Beverages', icon: '🥤' },
  'Snacks': { order: 12, aisle: 'Snacks', icon: '🍿' },
  'Cleaning': { order: 13, aisle: 'Household', icon: '🧹' },
  'Other': { order: 14, aisle: 'Other Items', icon: '📦' }
};

const ShoppingList = () => {
  const [shoppingList, setShoppingList] = useState([]);
  const [newItem, setNewItem] = useState({ name: '', category: 'Produce' });
  const [shoppingMode, setShoppingMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const voiceRecogRef = useRef(null);
  
  // Batch processing - debounce saves for cost efficiency
  const pendingUpdatesRef = useRef(null);
  const BATCH_DELAY = 1500;

  // Get auth token
  const getAuthToken = () => {
    return localStorage.getItem('token');
  };

  // Fetch shopping list from API
  const fetchShoppingList = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/shopping-list`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Transform flat items to categorized format for UI
        const categorized = transformToCategorized(data.items || []);
        setShoppingList(categorized);
      } else {
        console.error('Failed to fetch shopping list');
        toast.error('Failed to load shopping list');
      }
    } catch (err) {
      console.error('Error fetching shopping list:', err);
      toast.error('Error loading shopping list');
    } finally {
      setLoading(false);
    }
  }, []);

  // Transform flat items array to categorized format for UI
  const transformToCategorized = (items) => {
    const categoryMap = {};
    
    items.forEach(item => {
      const category = item.category || 'Other';
      if (!categoryMap[category]) {
        categoryMap[category] = {
          id: `cat_${category.toLowerCase().replace(/\s+/g, '_')}`,
          category: category,
          items: []
        };
      }
      categoryMap[category].items.push({
        id: item.item_id || item.id || `i${Date.now()}${Math.random()}`,
        name: item.name,
        amount: item.amount || '1',
        checked: item.checked || false,
        category: category
      });
    });

    return Object.values(categoryMap);
  };

  // Transform categorized format back to flat items for API
  const transformToFlat = (categorized) => {
    const flatItems = [];
    categorized.forEach(cat => {
      cat.items.forEach(item => {
        flatItems.push({
          item_id: item.id,
          name: item.name,
          amount: item.amount,
          checked: item.checked,
          category: cat.category
        });
      });
    });
    return flatItems;
  };

  // Batch save to API (debounced for cost efficiency)
  const saveToAPI = useCallback(async (listToSave) => {
    const token = getAuthToken();
    if (!token) return;

    setSaving(true);
    try {
      const flatItems = transformToFlat(listToSave);
      const response = await fetch(`${API_URL}/api/shopping-list`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ items: flatItems })
      });

      if (!response.ok) {
        throw new Error('Failed to save');
      }
    } catch (err) {
      console.error('Error saving shopping list:', err);
      toast.error('Failed to save changes');
    } finally {
      setSaving(false);
    }
  }, []);

  // Debounced batch save
  const scheduleSave = useCallback((newList) => {
    // Clear any pending save
    if (pendingUpdatesRef.current) {
      clearTimeout(pendingUpdatesRef.current);
    }
    
    // Schedule new save after delay (batch processing)
    pendingUpdatesRef.current = setTimeout(() => {
      saveToAPI(newList);
      pendingUpdatesRef.current = null;
    }, BATCH_DELAY);
  }, [saveToAPI]);

  // Update local state and schedule batch save
  const updateShoppingList = useCallback((newList) => {
    setShoppingList(newList);
    scheduleSave(newList);
  }, [scheduleSave]);

  // Load shopping list on mount
  useEffect(() => {
    fetchShoppingList();
    
    // Cleanup pending saves on unmount
    return () => {
      if (pendingUpdatesRef.current) {
        clearTimeout(pendingUpdatesRef.current);
      }
    };
  }, [fetchShoppingList]);

  const handleAddItem = () => {
    if (!newItem.name.trim()) return;
    
    const categoryIndex = shoppingList.findIndex(cat => cat.category === newItem.category);
    const newList = [...shoppingList];
    const newItemObj = {
      id: `i${Date.now()}`,
      name: newItem.name.trim(),
      amount: '1',
      checked: false,
      category: newItem.category
    };
    
    if (categoryIndex >= 0) {
      newList[categoryIndex] = {
        ...newList[categoryIndex],
        items: [...newList[categoryIndex].items, newItemObj]
      };
    } else {
      newList.push({
        id: `cat_${newItem.category.toLowerCase().replace(/\s+/g, '_')}`,
        category: newItem.category,
        items: [newItemObj]
      });
    }
    
    updateShoppingList(newList);
    setNewItem({ name: '', category: 'Produce' });
    toast.success('Item added');
  };

  // Voice input handler
  const handleVoiceInput = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error('Voice not supported in this browser'); return; }
    if (voiceListening) { voiceRecogRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = 'en-US';
    rec.interimResults = false;
    rec.onstart = () => setVoiceListening(true);
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setNewItem(prev => ({ ...prev, name: text }));
      setVoiceListening(false);
    };
    rec.onerror = () => setVoiceListening(false);
    rec.onend = () => setVoiceListening(false);
    voiceRecogRef.current = rec;
    rec.start();
  };

  const toggleShoppingItem = (categoryId, itemId) => {
    const newList = shoppingList.map(cat => 
      cat.id === categoryId ? {
        ...cat,
        items: cat.items.map(item => 
          item.id === itemId ? { ...item, checked: !item.checked } : item
        )
      } : cat
    );
    updateShoppingList(newList);
  };

  const handleDeleteItem = (categoryId, itemId) => {
    const newList = shoppingList.map(cat => {
      if (cat.id === categoryId) {
        return {
          ...cat,
          items: cat.items.filter(item => item.id !== itemId)
        };
      }
      return cat;
    }).filter(cat => cat.items.length > 0);
    
    updateShoppingList(newList);
    toast.success('Item removed');
  };

  const clearChecked = async () => {
    const newList = shoppingList.map(cat => ({
      ...cat,
      items: cat.items.filter(item => !item.checked)
    })).filter(cat => cat.items.length > 0);
    
    updateShoppingList(newList);
    toast.success('Checked items cleared');
  };

  const clearAll = async () => {
    const token = getAuthToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/shopping-list`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setShoppingList([]);
        toast.success('Shopping list cleared');
      }
    } catch (err) {
      console.error('Error clearing shopping list:', err);
      toast.error('Failed to clear list');
    }
  };

  // Get all items sorted by supermarket aisle
  const getSortedItemsForShoppingMode = () => {
    const allItems = [];
    
    shoppingList.forEach(category => {
      category.items.forEach(item => {
        allItems.push({
          ...item,
          category: category.category,
          categoryId: category.id
        });
      });
    });
    
    // Group by aisle
    const aisleGroups = {};
    allItems.forEach(item => {
      const aisleInfo = AISLE_ORDER[item.category] || AISLE_ORDER['Other'];
      const aisleName = aisleInfo.aisle;
      
      if (!aisleGroups[aisleName]) {
        aisleGroups[aisleName] = {
          name: aisleName,
          order: aisleInfo.order,
          icon: aisleInfo.icon,
          items: []
        };
      }
      aisleGroups[aisleName].items.push(item);
    });
    
    // Sort aisles by order and return
    return Object.values(aisleGroups).sort((a, b) => a.order - b.order);
  };

  const totalItems = shoppingList.reduce((sum, cat) => sum + cat.items.length, 0);
  const checkedItems = shoppingList.reduce((sum, cat) => 
    sum + cat.items.filter(item => item.checked).length, 0
  );
  const uncheckedItems = totalItems - checkedItems;

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-zinc-400">Loading your shopping list...</p>
        </div>
      </div>
    );
  }

  // Shopping Mode View - Full screen simple list
  if (shoppingMode) {
    const sortedAisles = getSortedItemsForShoppingMode();
    
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100">
        {/* Header */}
        <div className="sticky z-20 bg-zinc-900 border-b border-zinc-800 px-4 py-4" style={{ top: 'var(--top-nav-h)' }}>
          <div className="max-w-2xl mx-auto flex items-center justify-between">
            <button
              onClick={() => setShoppingMode(false)}
              className="flex items-center gap-2 text-zinc-400 hover:text-zinc-100 transition-colors"
              data-testid="exit-shopping-mode"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Exit</span>
            </button>
            <h1 className="font-semibold text-lg text-zinc-100">Shopping Mode</h1>
            <div className="text-sm text-zinc-400 flex items-center gap-2">
              {saving && <Loader2 className="w-3 h-3 animate-spin" />}
              {checkedItems}/{totalItems}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="sticky top-[65px] z-10 bg-zinc-900 px-4 py-2">
          <div className="max-w-2xl mx-auto">
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-orange-600 to-orange-500 transition-all duration-300"
                style={{ width: `${totalItems > 0 ? (checkedItems / totalItems) * 100 : 0}%` }}
              />
            </div>
            <p className="text-xs text-zinc-500 mt-1 text-center">
              {uncheckedItems} items remaining
            </p>
          </div>
        </div>

        {/* Shopping List by Aisle */}
        <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
          {sortedAisles.length > 0 ? (
            <div className="space-y-6">
              {sortedAisles.map((aisle, aisleIdx) => (
                <div key={aisleIdx} className="space-y-2">
                  {/* Aisle Header */}
                  <div className="flex items-center gap-2 px-2 py-2 bg-zinc-800/50 rounded-lg sticky top-[105px] z-5">
                    <span className="text-xl">{aisle.icon}</span>
                    <h2 className="font-semibold text-zinc-200">{aisle.name}</h2>
                    <span className="text-xs text-zinc-500 ml-auto">
                      {aisle.items.filter(i => i.checked).length}/{aisle.items.length}
                    </span>
                  </div>
                  
                  {/* Items */}
                  <div className="space-y-1">
                    {aisle.items.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => toggleShoppingItem(item.categoryId, item.id)}
                        className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all ${
                          item.checked 
                            ? 'bg-zinc-800/30 opacity-60' 
                            : 'bg-zinc-900 border border-zinc-800'
                        }`}
                        data-testid={`shopping-item-${item.id}`}
                      >
                        <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-colors ${
                          item.checked
                            ? 'bg-orange-600 border-orange-600'
                            : 'border-zinc-600'
                        }`}>
                          {item.checked && <Check className="w-4 h-4 text-white" />}
                        </div>
                        <span className={`flex-1 text-left text-lg ${
                          item.checked ? 'line-through text-zinc-600' : 'text-zinc-100'
                        }`}>
                          {item.name}
                        </span>
                        {item.amount && (
                          <span className="text-sm text-zinc-500">
                            {item.amount}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <ShoppingCart className="w-16 h-16 mx-auto text-zinc-700 mb-4" />
              <p className="text-zinc-500">Your shopping list is empty</p>
            </div>
          )}
        </div>

        {/* Completion Banner */}
        {checkedItems === totalItems && totalItems > 0 && (
          <div className="fixed left-0 right-0 z-40 bg-gradient-to-r from-green-600 to-emerald-600 p-4" style={{ bottom: 'var(--bottom-nav-h)' }}>
            <div className="max-w-2xl mx-auto text-center">
              <p className="text-white font-semibold text-lg">🎉 All done! Great shopping!</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Normal View
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero Header */}
      <div className="relative h-[25vh] min-h-[200px]">
        <img 
          src="https://images.unsplash.com/photo-1542838132-92c53300491e?w=1920&h=600&fit=crop"
          alt="Shopping"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <div>
              <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">
                Shopping List
              </h1>
              <p className="text-zinc-400 mt-2">
                {checkedItems} of {totalItems} items checked
                {saving && <span className="ml-2 text-orange-400">(saving...)</span>}
              </p>
            </div>
            <Button
              onClick={fetchShoppingList}
              variant="ghost"
              size="icon"
              className="text-zinc-400 hover:text-zinc-100"
              data-testid="refresh-shopping-list"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Add Item */}
        <Card className="mb-6 bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-zinc-100">Add Item</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex gap-2 flex-1">
                <Input
                  value={newItem.name}
                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                  placeholder="Item name"
                  className="flex-1 bg-zinc-950 border-zinc-800 text-zinc-100"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddItem()}
                  data-testid="shopping-item-input"
                />
                <button
                  onClick={handleVoiceInput}
                  title="Add item by voice"
                  className={`px-3 rounded-lg border transition-colors ${voiceListening ? 'bg-red-600 border-red-600 text-white animate-pulse' : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-orange-600 hover:text-orange-500'}`}
                >
                  {voiceListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              </div>
              <select
                value={newItem.category}
                onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                className="px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100 focus:outline-none focus:ring-2 focus:ring-orange-600"
                data-testid="shopping-category-select"
              >
                <option value="Produce">Produce</option>
                <option value="Meat">Meat</option>
                <option value="Seafood">Seafood</option>
                <option value="Dairy">Dairy</option>
                <option value="Bakery">Bakery</option>
                <option value="Frozen">Frozen</option>
                <option value="Pantry">Pantry</option>
                <option value="Canned">Canned</option>
                <option value="Grains">Grains</option>
                <option value="Spices">Spices</option>
                <option value="Oils">Oils</option>
                <option value="Condiments">Condiments</option>
                <option value="Beverages">Beverages</option>
                <option value="Snacks">Snacks</option>
                <option value="Baking">Baking</option>
                <option value="Cleaning">Household</option>
                <option value="Other">Other</option>
              </select>
              <Button onClick={handleAddItem} className="bg-orange-600 hover:bg-orange-700" data-testid="add-shopping-item-btn">
                <Plus className="w-5 h-5 mr-2" />
                Add
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Shopping Mode & Clear Buttons */}
        <div className="mb-6 flex flex-col sm:flex-row gap-3">
          <Button 
            onClick={() => setShoppingMode(true)}
            disabled={totalItems === 0}
            className="flex-1 bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-700 hover:to-orange-600 text-white h-12"
            data-testid="start-shopping-mode"
          >
            <ShoppingBag className="w-5 h-5 mr-2" />
            Start Shopping Mode
            {uncheckedItems > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-white/20 rounded-full text-sm">
                {uncheckedItems} items
              </span>
            )}
          </Button>
          
          {checkedItems > 0 && (
            <Button 
              onClick={clearChecked} 
              variant="outline" 
              className="text-red-500 border-red-500/50 hover:bg-red-500/10"
              data-testid="clear-checked-btn"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Checked ({checkedItems})
            </Button>
          )}

          {totalItems > 0 && (
            <Button 
              onClick={clearAll} 
              variant="outline" 
              className="text-zinc-500 border-zinc-700 hover:bg-zinc-800"
              data-testid="clear-all-btn"
            >
              Clear All
            </Button>
          )}
        </div>

        {/* Shopping List by Category */}
        <div className="space-y-4">
          {shoppingList.length > 0 ? (
            shoppingList.map((category) => (
              <Card key={category.id} className="bg-zinc-900 border-zinc-800">
                <CardHeader className="bg-zinc-800/50">
                  <CardTitle className="text-lg text-zinc-100 flex items-center gap-2">
                    <span>{AISLE_ORDER[category.category]?.icon || '📦'}</span>
                    {category.category} ({category.items.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    {category.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/30 hover:bg-zinc-800/50 transition-colors"
                        data-testid={`shopping-list-item-${item.id}`}
                      >
                        <div className="flex items-center space-x-3 flex-1">
                          <button
                            onClick={() => toggleShoppingItem(category.id, item.id)}
                            className={`w-6 h-6 rounded border-2 flex items-center justify-center transition-colors ${
                              item.checked
                                ? 'bg-orange-600 border-orange-600'
                                : 'border-zinc-600 hover:border-orange-600'
                            }`}
                            data-testid={`check-${item.id}`}
                          >
                            {item.checked && <Check className="w-4 h-4 text-white" />}
                          </button>
                          <span className={`${
                            item.checked ? 'line-through text-zinc-600' : 'text-zinc-100'
                          }`}>
                            {item.name}
                          </span>
                          <span className="text-zinc-600 text-sm">({item.amount})</span>
                        </div>
                        <button
                          onClick={() => handleDeleteItem(category.id, item.id)}
                          className="p-1 text-red-500 hover:bg-red-500/10 rounded"
                          data-testid={`delete-${item.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
                <ShoppingCart className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-400 text-lg">Your shopping list is empty</p>
              <p className="text-zinc-600 mt-2">Add items manually or from recipes</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShoppingList;
