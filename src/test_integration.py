#!/usr/bin/env python3
"""
Integration test to verify the GUI changes work correctly
"""

import tempfile
import os
import inspect
from logic import BudgetLogic

def test_gui_structure():
    """Test that the GUI code has the new category management features"""
    
    # Import the GUI module
    import gui
    
    # Check that the GUI class has the expected methods
    gui_methods = [name for name, _ in inspect.getmembers(gui.BudgetAppGUI, predicate=inspect.isfunction)]
    
    expected_methods = [
        'add_new_category_row',
        'remove_selected_category', 
        'load_budget_grid',
        'edit_budget_cell',
        'refresh_categories'
    ]
    
    for method in expected_methods:
        assert method in gui_methods, f"GUI should have {method} method"
    
    print("✓ GUI has all expected category management methods")
    
    # Check that there's no old category tab methods
    old_methods = ['add_category', 'remove_category']  # These would be the old tab methods
    
    for method in old_methods:
        if method in gui_methods:
            # Check if it's the new integrated version by checking if it operates on budget_tree
            import ast
            source = inspect.getsource(getattr(gui.BudgetAppGUI, method))
            if 'category_list' in source:
                assert False, f"Old category tab method {method} still references category_list"
    
    print("✓ Old category tab methods have been properly removed/updated")

def test_logic_integration():
    """Test that the logic layer works correctly for category management"""
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    # Remove the empty file so the logic will create a new encrypted database
    os.unlink(db_path)
    
    try:
        # Initialize the logic layer
        logic = BudgetLogic(db_path, "test_password")
        
        # Test adding a category
        logic.add_category("Test Category")
        categories = logic.get_categories()
        assert "Test Category" in categories, "Category should be added"
        
        # Test budget setting
        logic.set_budget("Test Category", 2024, 1000.0)
        budget = logic.get_budget("Test Category", 2024)
        assert budget == 1000.0, "Budget should be set correctly"
        
        # Test removing category with cascading effects
        logic.remove_category("Test Category")
        categories_after = logic.get_categories()
        assert "Test Category" not in categories_after, "Category should be removed"
        
        # Check that budget was also removed
        budget_after = logic.get_budget("Test Category", 2024)
        assert budget_after == 0.0, "Budget should return 0.0 when category is removed"
        
        print("✓ Category and budget operations work correctly")
        print("✓ Category removal properly cascades to budgets")
        
        # Clean up
        logic.close()
        
        print("✓ All integration tests passed!")
        
    finally:
        # Clean up temp file
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    test_gui_structure()
    test_logic_integration()
