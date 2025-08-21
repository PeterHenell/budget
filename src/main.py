#!/usr/bin/env python3
"""
Budget App - Main Entry Point

A Python budget application with GUI for managing monthly budgets by category,
importing transactions from CSV, and generating spending reports.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox, simpledialog

def prompt_password():
    """Prompt user for database password"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    pw = simpledialog.askstring(
        "Budget App - Database Password", 
        "Enter database password:", 
        show='*'
    )
    root.destroy()
    return pw

def main():
    """Main application entry point"""
    try:
        # Get password
        password = prompt_password()
        if not password:
            print("Password required to start application.")
            return 1
            
        # Import and initialize
        from logic import BudgetLogic
        from gui import BudgetAppGUI
        
        # Initialize logic with encrypted database
        db_path = "budget.db"
        logic = BudgetLogic(db_path, password)
        
        # Create and run GUI
        app = BudgetAppGUI(logic)
        
        # Handle window close to ensure proper cleanup
        def on_close():
            try:
                logic.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                app.destroy()
                
        app.protocol("WM_DELETE_WINDOW", on_close)
        
        print("Budget App started successfully!")
        app.mainloop()
        
        return 0
        
    except Exception as e:
        # Show error in GUI if possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Budget App Error", f"Failed to start application:\n{e}")
            root.destroy()
        except:
            pass
            
        print(f"Error starting application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
