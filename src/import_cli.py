#!/usr/bin/env python3
"""
Command-line CSV import utility for the Budget App.
Processes CSV files from the input folder, allows interactive categorization,
and archives processed files.
"""

import os
import shutil
import getpass
from pathlib import Path
from logic import BudgetLogic


def get_database_password():
    """Get the database password from the user."""
    while True:
        password = getpass.getpass("Enter database password: ")
        if password:
            return password
        print("Password cannot be empty. Please try again.")


def display_categories(categories):
    """Display the available categories with numbers."""
    print("\nAvailable categories:")
    for i, category in enumerate(categories, 1):
        print(f"  {i}. {category}")
    print("  0. Skip this transaction (leave unclassified)")


def get_category_choice(categories):
    """Get the user's category choice."""
    while True:
        try:
            choice = input(f"Enter category number (1-{len(categories)}, 0 to skip): ").strip()
            if choice == "0":
                return None  # Skip/unclassified
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(categories):
                return categories[choice_num - 1]
            else:
                print(f"Please enter a number between 0 and {len(categories)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\nImport cancelled by user.")
            return "CANCEL"


def format_transaction_display(tx):
    """Format a transaction for display."""
    verif_num, date, description, amount = tx
    amount_str = f"{amount:,.2f}" if amount < 0 else f"+{amount:,.2f}"
    return f"Date: {date} | Amount: {amount_str} | Description: {description}"


def import_csv_interactive(logic, csv_path):
    """Import a CSV file with optional interactive categorization."""
    print(f"\nProcessing: {os.path.basename(csv_path)}")
    
    try:
        # Import transactions (they will be automatically assigned to "Uncategorized")
        count = logic.import_csv(csv_path)
        print(f"Imported {count} transactions from CSV")
        
        if count == 0:
            print("No new transactions to process.")
            return True
        
        print(f"All {count} transactions have been imported and placed in the 'Uncategorized' category.")
        print("You can classify them later using the GUI's 'Uncategorized Queue' tab.")
        
        # Ask if user wants to classify now
        classify_now = input("\nWould you like to classify some transactions now? (y/n): ").lower().strip()
        if classify_now != 'y':
            return True
        
        # Get unclassified transactions (this will return empty now since all go to Uncategorized)
        # Instead, get uncategorized transactions
        uncategorized = logic.get_uncategorized_transactions(limit=50)  # Limit to first 50 for CLI
        if not uncategorized:
            print("No uncategorized transactions found.")
            return True
        
        print(f"\nFound {len(uncategorized)} uncategorized transactions (showing first 50).")
        
        # Get categories (excluding Uncategorized)
        categories = [cat for cat in logic.get_categories() if cat != "Uncategorized"]
        if not categories:
            print("No categories found besides 'Uncategorized'. Please add categories first through the GUI.")
            return True
        
        # Interactive classification
        classified_count = 0
        skipped_count = 0
        
        for i, tx in enumerate(uncategorized, 1):
            tx_id, verif_num, date, description, amount, year, month = tx
            print(f"\n--- Transaction {i} of {len(uncategorized)} ---")
            print(f"Date: {date} | Amount: {amount:,.2f} | Description: {description}")
            
            display_categories(categories)
            
            choice = get_category_choice(categories)
            if choice == "CANCEL":
                return False
            elif choice is None:
                print("Skipping transaction (staying in Uncategorized)")
                skipped_count += 1
            else:
                try:
                    logic.reclassify_transaction(tx_id, choice)
                    print(f"Classified as: {choice}")
                    classified_count += 1
                except Exception as e:
                    print(f"Error classifying transaction: {e}")
                    skipped_count += 1
        
        print(f"\n--- Classification Summary ---")
        print(f"Transactions classified: {classified_count}")
        print(f"Transactions left uncategorized: {skipped_count}")
        
        # Show remaining uncategorized count
        remaining = logic.get_uncategorized_count()
        if remaining > 0:
            print(f"Total remaining uncategorized transactions: {remaining}")
            print("Use the GUI's 'Uncategorized Queue' tab to classify the rest.")
        
        return True
        
    except Exception as e:
        print(f"Error importing CSV {csv_path}: {e}")
        return False


def find_csv_files(input_dir):
    """Find all CSV files in the input directory."""
    csv_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        return csv_files
    
    for file_path in input_path.glob("*.csv"):
        if file_path.is_file():
            csv_files.append(file_path)
    
    return sorted(csv_files)  # Sort for consistent processing order


def archive_file(file_path, archive_dir):
    """Move a file to the archive directory."""
    archive_path = Path(archive_dir)
    archive_path.mkdir(exist_ok=True)  # Create archive dir if it doesn't exist
    
    destination = archive_path / file_path.name
    
    # Handle filename conflicts by adding a number
    counter = 1
    while destination.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        destination = archive_path / f"{stem}_{counter}{suffix}"
        counter += 1
    
    shutil.move(str(file_path), str(destination))
    return destination


def main():
    """Main function for the CLI import utility."""
    print("=== Budget App - CSV Import Utility ===")
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "input"
    archive_dir = project_root / "archive"
    db_path = project_root / "budget.db"
    
    # Check for CSV files
    csv_files = find_csv_files(input_dir)
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        print("Place CSV files in the 'input' folder and run this script again.")
        return
    
    print(f"Found {len(csv_files)} CSV file(s) to process:")
    for csv_file in csv_files:
        print(f"  - {csv_file.name}")
    
    # Get database password
    password = get_database_password()
    
    # Initialize database connection
    try:
        with BudgetLogic(str(db_path), password) as logic:
            print("Database connection established.")
            
            successful_imports = []
            failed_imports = []
            
            # Process each CSV file
            for csv_file in csv_files:
                try:
                    success = import_csv_interactive(logic, str(csv_file))
                    if success:
                        successful_imports.append(csv_file)
                    else:
                        failed_imports.append(csv_file)
                        print(f"Failed to process {csv_file.name}")
                        
                        # Ask if user wants to continue with next file
                        if len(csv_files) > 1:
                            continue_choice = input("\nContinue with next file? (y/n): ").lower().strip()
                            if continue_choice != 'y':
                                break
                    
                except KeyboardInterrupt:
                    print("\n\nImport cancelled by user.")
                    failed_imports.append(csv_file)
                    break
                except Exception as e:
                    print(f"Unexpected error processing {csv_file.name}: {e}")
                    failed_imports.append(csv_file)
            
            # Archive successfully processed files
            archived_files = []
            for csv_file in successful_imports:
                try:
                    archived_location = archive_file(csv_file, archive_dir)
                    archived_files.append(archived_location)
                    print(f"Archived: {csv_file.name} -> {archived_location.name}")
                except Exception as e:
                    print(f"Warning: Could not archive {csv_file.name}: {e}")
            
            # Final summary
            print(f"\n=== Final Summary ===")
            print(f"Files processed successfully: {len(successful_imports)}")
            print(f"Files failed: {len(failed_imports)}")
            print(f"Files archived: {len(archived_files)}")
            
            if failed_imports:
                print(f"\nFailed files (left in input folder):")
                for failed_file in failed_imports:
                    print(f"  - {failed_file.name}")
    
    except ValueError as e:
        if "password" in str(e).lower():
            print("Error: Incorrect password or corrupted database file.")
        else:
            print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
