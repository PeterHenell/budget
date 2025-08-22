import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

class BudgetAppGUI(tk.Tk):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.title("Budget App")
        self.geometry("900x700")
        self.create_widgets()

    def create_widgets(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        # Budget tab (Categories tab removed - categories managed here)
        self.tab_budget = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_budget, text="Budgets")
        
        # Year selection frame
        budget_controls = tk.Frame(self.tab_budget)
        budget_controls.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(budget_controls, text="Year:").pack(side=tk.LEFT)
        self.budget_year = tk.Entry(budget_controls, width=8)
        self.budget_year.pack(side=tk.LEFT, padx=5)
        self.budget_year.insert(0, "2025")  # Default year
        
        tk.Label(budget_controls, text="(Budgets are set per year and apply to all months)").pack(side=tk.LEFT, padx=10)
        
        tk.Button(budget_controls, text="Load Budgets", command=self.load_budget_grid).pack(side=tk.LEFT, padx=10)
        tk.Button(budget_controls, text="Add Category", command=self.add_new_category_row).pack(side=tk.LEFT, padx=5)
        tk.Button(budget_controls, text="Remove Selected", command=self.remove_selected_category).pack(side=tk.LEFT, padx=5)
        
        # Budget grid
        grid_frame = tk.Frame(self.tab_budget)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Treeview for budget grid
        columns = ("Category", "Yearly Budget")
        self.budget_tree = ttk.Treeview(grid_frame, columns=columns, show="headings", height=15)
        
        # Configure column headings and widths
        self.budget_tree.heading("Category", text="Category")
        self.budget_tree.heading("Yearly Budget", text="Yearly Budget (SEK)")
        self.budget_tree.column("Category", width=200)
        self.budget_tree.column("Yearly Budget", width=150)
        
        # Add scrollbar
        budget_scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.budget_tree.yview)
        self.budget_tree.configure(yscrollcommand=budget_scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.budget_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        budget_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to edit
        self.budget_tree.bind("<Double-1>", self.edit_budget_cell)
        
        # Load initial budget grid
        self.load_budget_grid()

        # Import tab
        self.tab_import = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_import, text="Import CSV")
        tk.Button(self.tab_import, text="Import CSV", command=self.import_csv).pack()

        # Classification tab
        self.tab_classify = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_classify, text="Classify Transactions")
        self.classify_list = tk.Listbox(self.tab_classify)
        self.classify_list.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.tab_classify, text="Classify Selected", command=self.classify_selected).pack()
        self.refresh_unclassified()

        # Uncategorized Transactions tab
        self.tab_uncategorized = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_uncategorized, text="Uncategorized Queue")
        self.setup_uncategorized_tab()

        # Report tab
        self.tab_report = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_report, text="Report")
        
        # Report controls
        report_controls = tk.Frame(self.tab_report)
        report_controls.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(report_controls, text="Year:").pack(side=tk.LEFT)
        self.report_year = tk.Entry(report_controls, width=8)
        self.report_year.pack(side=tk.LEFT, padx=5)
        self.report_year.insert(0, "2025")  # Default year
        
        tk.Label(report_controls, text="Month (optional):").pack(side=tk.LEFT, padx=(10,0))
        self.report_month = tk.Entry(report_controls, width=8)
        self.report_month.pack(side=tk.LEFT, padx=5)
        self.report_month.insert(0, "8")  # Default month
        
        tk.Button(report_controls, text="Monthly Report", command=self.show_monthly_report).pack(side=tk.LEFT, padx=10)
        tk.Button(report_controls, text="Yearly Report", command=self.show_yearly_report).pack(side=tk.LEFT, padx=5)
        
        # Report tree
        self.report_tree = ttk.Treeview(self.tab_report, columns=("Category", "Spent", "Budget", "Diff", "Percent"), show="headings")
        for col in ("Category", "Spent", "Budget", "Diff", "Percent"):
            self.report_tree.heading(col, text=col)
            if col == "Category":
                self.report_tree.column(col, width=150)
            else:
                self.report_tree.column(col, width=100)
        self.report_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_uncategorized_tab(self):
        """Setup the uncategorized transactions management tab"""
        # Top controls frame
        controls_frame = tk.Frame(self.tab_uncategorized)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Count label
        self.uncategorized_count_label = tk.Label(controls_frame, text="Loading...")
        self.uncategorized_count_label.pack(side=tk.LEFT)
        
        # Refresh button
        tk.Button(controls_frame, text="Refresh", command=self.refresh_uncategorized_queue).pack(side=tk.RIGHT, padx=5)
        
        # Batch classify button
        tk.Button(controls_frame, text="Batch Classify", command=self.batch_classify_dialog).pack(side=tk.RIGHT, padx=5)
        
        # Auto-classify button
        tk.Button(controls_frame, text="Auto Classify", command=self.auto_classify_dialog, 
                 bg="lightcoral").pack(side=tk.RIGHT, padx=5)
        
        # Main frame for treeview and category selection
        main_frame = tk.Frame(self.tab_uncategorized)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Transaction list
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(left_frame, text="Uncategorized Transactions:").pack(anchor='w')
        
        # Treeview for transactions
        columns = ("Date", "Description", "Amount")
        self.uncategorized_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.uncategorized_tree.heading("Date", text="Date")
        self.uncategorized_tree.heading("Description", text="Description") 
        self.uncategorized_tree.heading("Amount", text="Amount")
        
        self.uncategorized_tree.column("Date", width=100)
        self.uncategorized_tree.column("Description", width=300)
        self.uncategorized_tree.column("Amount", width=100)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.uncategorized_tree.yview)
        self.uncategorized_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Pack treeview and scrollbar
        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.uncategorized_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right side - Category selection and actions
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        tk.Label(right_frame, text="Categorize Selected:").pack(anchor='w')
        
        # Category selection
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(right_frame, textvariable=self.category_var, 
                                            state="readonly", width=20)
        self.category_dropdown.pack(pady=5, fill=tk.X)
        
        # Classify button
        tk.Button(right_frame, text="Classify Selected", 
                 command=self.classify_selected_uncategorized,
                 bg="lightgreen").pack(pady=5, fill=tk.X)
        
        # Separator
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Multiple selection actions
        tk.Label(right_frame, text="Multi-select Actions:").pack(anchor='w')
        tk.Label(right_frame, text="(Hold Ctrl to select multiple)", 
                font=("Arial", 8), fg="gray").pack(anchor='w')
        
        tk.Button(right_frame, text="Classify Multiple", 
                 command=self.classify_multiple_uncategorized,
                 bg="lightblue").pack(pady=2, fill=tk.X)
        
        # Pagination controls
        pagination_frame = tk.Frame(self.tab_uncategorized)
        pagination_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.current_page = 0
        self.items_per_page = 100
        
        tk.Button(pagination_frame, text="<< Previous", command=self.prev_page).pack(side=tk.LEFT)
        self.page_label = tk.Label(pagination_frame, text="Page 1")
        self.page_label.pack(side=tk.LEFT, padx=10)
        tk.Button(pagination_frame, text="Next >>", command=self.next_page).pack(side=tk.LEFT)
        
        # Load initial data
        self.refresh_uncategorized_queue()

    def refresh_uncategorized_queue(self):
        """Refresh the uncategorized transactions display"""
        try:
            # Update count
            total_count = self.logic.get_uncategorized_count()
            self.uncategorized_count_label.config(text=f"Total uncategorized: {total_count}")
            
            # Update categories dropdown
            categories = [cat for cat in self.logic.get_categories() if cat != "Uncategorized"]
            self.category_dropdown['values'] = categories
            if categories and not self.category_var.get():
                self.category_var.set(categories[0])
            
            # Load transactions for current page
            offset = self.current_page * self.items_per_page
            transactions = self.logic.get_uncategorized_transactions(
                limit=self.items_per_page, 
                offset=offset
            )
            
            # Clear existing data
            for item in self.uncategorized_tree.get_children():
                self.uncategorized_tree.delete(item)
            
            # Add transactions to tree (store transaction ID as well)
            for tx in transactions:
                tx_id, verif_num, date, description, amount, year, month = tx
                amount_str = f"{amount:,.2f}"
                if amount >= 0:
                    amount_str = f"+{amount_str}"
                    
                # Insert with transaction ID stored as the item identifier
                self.uncategorized_tree.insert("", tk.END, iid=str(tx_id),
                                             values=(date, description, amount_str))
            
            # Update page label
            max_pages = (total_count + self.items_per_page - 1) // self.items_per_page
            self.page_label.config(text=f"Page {self.current_page + 1} of {max_pages}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh uncategorized transactions: {e}")

    def classify_selected_uncategorized(self):
        """Classify the selected uncategorized transaction"""
        selection = self.uncategorized_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a transaction to classify.")
            return
            
        category = self.category_var.get()
        if not category:
            messagebox.showwarning("Warning", "Please select a category.")
            return
            
        try:
            # Get transaction ID from selection
            tx_id = int(selection[0])  # We stored tx_id as the item identifier
            
            # Reclassify the transaction
            self.logic.reclassify_transaction(tx_id, category)
            
            # Refresh display
            self.refresh_uncategorized_queue()
            
            messagebox.showinfo("Success", f"Transaction classified as '{category}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to classify transaction: {e}")

    def classify_multiple_uncategorized(self):
        """Classify multiple selected transactions"""
        selection = self.uncategorized_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select transactions to classify.")
            return
            
        category = self.category_var.get()
        if not category:
            messagebox.showwarning("Warning", "Please select a category.")
            return
            
        # Confirm batch classification
        if not messagebox.askyesno("Confirm", 
                                  f"Classify {len(selection)} transactions as '{category}'?"):
            return
        
        try:
            classified_count = 0
            for item_id in selection:
                tx_id = int(item_id)  # We stored tx_id as the item identifier
                self.logic.reclassify_transaction(tx_id, category)
                classified_count += 1
            
            # Refresh display
            self.refresh_uncategorized_queue()
            
            messagebox.showinfo("Success", 
                              f"{classified_count} transactions classified as '{category}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to classify transactions: {e}")

    def batch_classify_dialog(self):
        """Open dialog for batch classification rules"""
        dialog = tk.Toplevel(self)
        dialog.title("Batch Classification")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        tk.Label(dialog, text="Batch classify transactions by description keywords:", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Keywords entry
        tk.Label(dialog, text="Keywords (comma-separated):").pack(anchor='w', padx=20)
        keywords_entry = tk.Entry(dialog, width=50)
        keywords_entry.pack(pady=5, padx=20, fill=tk.X)
        
        # Category selection
        tk.Label(dialog, text="Category:").pack(anchor='w', padx=20, pady=(10,0))
        batch_category_var = tk.StringVar()
        categories = [cat for cat in self.logic.get_categories() if cat != "Uncategorized"]
        batch_category_combo = ttk.Combobox(dialog, textvariable=batch_category_var, 
                                          values=categories, state="readonly")
        batch_category_combo.pack(pady=5, padx=20, fill=tk.X)
        if categories:
            batch_category_var.set(categories[0])
        
        # Case sensitive checkbox
        case_sensitive_var = tk.BooleanVar()
        tk.Checkbutton(dialog, text="Case sensitive matching", 
                      variable=case_sensitive_var).pack(pady=5, padx=20, anchor='w')
        
        # Preview area
        tk.Label(dialog, text="Preview matching transactions:").pack(anchor='w', padx=20, pady=(10,0))
        preview_text = tk.Text(dialog, height=6, width=50)
        preview_text.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        def preview_matches():
            keywords = keywords_entry.get().strip()
            if not keywords:
                preview_text.delete(1.0, tk.END)
                return
                
            keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
            case_sensitive = case_sensitive_var.get()
            
            # Get uncategorized transactions
            transactions = self.logic.get_uncategorized_transactions()
            matches = []
            
            for tx in transactions:
                tx_id, verif_num, date, description, amount, year, month = tx
                desc_check = description if case_sensitive else description.lower()
                
                for keyword in keyword_list:
                    keyword_check = keyword if case_sensitive else keyword.lower()
                    if keyword_check in desc_check:
                        matches.append((tx_id, date, description, amount))
                        break
            
            # Update preview
            preview_text.delete(1.0, tk.END)
            if matches:
                preview_text.insert(tk.END, f"Found {len(matches)} matches:\n\n")
                for i, (tx_id, date, desc, amount) in enumerate(matches[:10]):  # Show first 10
                    preview_text.insert(tk.END, f"{date} | {amount:,.2f} | {desc}\n")
                if len(matches) > 10:
                    preview_text.insert(tk.END, f"\n... and {len(matches) - 10} more")
            else:
                preview_text.insert(tk.END, "No matching transactions found.")
        
        def apply_batch_classification():
            keywords = keywords_entry.get().strip()
            category = batch_category_var.get()
            
            if not keywords or not category:
                messagebox.showwarning("Warning", "Please enter keywords and select a category.")
                return
                
            keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
            case_sensitive = case_sensitive_var.get()
            
            # Find and classify matching transactions
            transactions = self.logic.get_uncategorized_transactions()
            classified_count = 0
            
            for tx in transactions:
                tx_id, verif_num, date, description, amount, year, month = tx
                desc_check = description if case_sensitive else description.lower()
                
                for keyword in keyword_list:
                    keyword_check = keyword if case_sensitive else keyword.lower()
                    if keyword_check in desc_check:
                        try:
                            self.logic.reclassify_transaction(tx_id, category)
                            classified_count += 1
                        except Exception as e:
                            print(f"Error classifying transaction {tx_id}: {e}")
                        break
            
            dialog.destroy()
            self.refresh_uncategorized_queue()
            messagebox.showinfo("Success", 
                              f"{classified_count} transactions classified as '{category}'")
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Preview", command=preview_matches).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Apply", command=apply_batch_classification, 
                 bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to preview
        keywords_entry.bind('<KeyRelease>', lambda e: preview_matches())

    def auto_classify_dialog(self):
        """Open dialog for automatic classification using multiple strategies"""
        try:
            # Import auto-classification modules
            from auto_classify import AutoClassificationEngine
            
            # Create classification engine
            engine = AutoClassificationEngine(self.logic)
            
            dialog = tk.Toplevel(self)
            dialog.title("Auto Classification")
            dialog.geometry("500x400")
            dialog.grab_set()
            
            tk.Label(dialog, text="Automatic Transaction Classification", 
                    font=("Arial", 14, "bold")).pack(pady=10)
            
            # Strategy explanation
            strategy_frame = tk.Frame(dialog)
            strategy_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(strategy_frame, text="Available Classification Strategies:", 
                    font=("Arial", 10, "bold")).pack(anchor='w')
            tk.Label(strategy_frame, text="• Rule-based: Swedish merchant patterns").pack(anchor='w')
            tk.Label(strategy_frame, text="• Learning: Based on your existing classifications").pack(anchor='w')
            
            # Check for additional classifiers
            try:
                from advanced_classify import SKLEARN_AVAILABLE, OLLAMA_AVAILABLE
                if SKLEARN_AVAILABLE:
                    tk.Label(strategy_frame, text="• Machine Learning: Advanced ML classification").pack(anchor='w')
                if OLLAMA_AVAILABLE:
                    tk.Label(strategy_frame, text="• Local LLM: AI-powered classification").pack(anchor='w')
            except ImportError:
                pass
            
            # Confidence threshold
            tk.Label(dialog, text="Confidence Threshold:", 
                    font=("Arial", 10, "bold")).pack(anchor='w', padx=20, pady=(10,0))
            
            confidence_frame = tk.Frame(dialog)
            confidence_frame.pack(fill=tk.X, padx=20, pady=5)
            
            confidence_var = tk.DoubleVar(value=0.8)
            confidence_scale = tk.Scale(confidence_frame, from_=0.5, to=0.95, resolution=0.05,
                                      orient=tk.HORIZONTAL, variable=confidence_var)
            confidence_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            confidence_label = tk.Label(confidence_frame, text="80%")
            confidence_label.pack(side=tk.RIGHT)
            
            def update_confidence_label():
                confidence_label.config(text=f"{int(confidence_var.get()*100)}%")
            
            confidence_scale.config(command=lambda v: update_confidence_label())
            
            tk.Label(dialog, text="Higher = more conservative, Lower = more suggestions", 
                    font=("Arial", 8), fg="gray").pack(anchor='w', padx=20)
            
            # Preview area
            tk.Label(dialog, text="Preview (showing first 10 transactions):", 
                    font=("Arial", 10, "bold")).pack(anchor='w', padx=20, pady=(15,5))
            
            preview_frame = tk.Frame(dialog)
            preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
            
            preview_text = tk.Text(preview_frame, height=8)
            preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_text.yview)
            preview_text.configure(yscrollcommand=preview_scrollbar.set)
            
            preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            def preview_classifications():
                threshold = confidence_var.get()
                preview_text.delete(1.0, tk.END)
                
                try:
                    # Get sample of uncategorized transactions
                    uncategorized = self.logic.get_uncategorized_transactions(limit=10)
                    
                    if not uncategorized:
                        preview_text.insert(tk.END, "No uncategorized transactions found.")
                        return
                    
                    preview_text.insert(tk.END, f"Classification preview (threshold: {int(threshold*100)}%):\\n\\n")
                    
                    auto_count = 0
                    review_count = 0
                    
                    for tx in uncategorized:
                        tx_id, verif_num, date, description, amount, year, month = tx
                        
                        transaction_data = {
                            'description': description,
                            'amount': amount,
                            'date': date,
                            'year': year,
                            'month': month
                        }
                        
                        suggestions = engine.classify_transaction(transaction_data)
                        
                        if suggestions and suggestions[0]['confidence'] >= threshold:
                            auto_count += 1
                            preview_text.insert(tk.END, 
                                f"AUTO: {description[:30]:<30} -> {suggestions[0]['category']} "
                                f"({suggestions[0]['confidence']:.1%})\\n")
                        elif suggestions and suggestions[0]['confidence'] >= 0.5:
                            review_count += 1
                            preview_text.insert(tk.END, 
                                f"REVIEW: {description[:30]:<30} -> {suggestions[0]['category']} "
                                f"({suggestions[0]['confidence']:.1%})\\n")
                        else:
                            preview_text.insert(tk.END, 
                                f"SKIP: {description[:30]:<30} -> No good match\\n")
                    
                    preview_text.insert(tk.END, f"\\nSummary: {auto_count} auto, {review_count} for review")
                    
                except Exception as e:
                    preview_text.insert(tk.END, f"Error generating preview: {e}")
            
            def apply_auto_classification():
                threshold = confidence_var.get()
                
                try:
                    classified_count, suggestions = engine.auto_classify_uncategorized(
                        confidence_threshold=threshold
                    )
                    
                    dialog.destroy()
                    self.refresh_uncategorized_queue()
                    
                    # Show results
                    result_msg = f"Auto-classified {classified_count} transactions.\\n"
                    if suggestions:
                        result_msg += f"{len(suggestions)} transactions need manual review.\\n\\n"
                        result_msg += "Top suggestions for review:\\n"
                        for item in suggestions[:5]:
                            result_msg += f"• {item['description'][:40]} -> {item['suggestions'][0]['category']}\\n"
                    
                    messagebox.showinfo("Auto Classification Results", result_msg)
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Auto-classification failed: {e}")
            
            # Buttons
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=15)
            
            tk.Button(button_frame, text="Preview", command=preview_classifications).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Apply Auto-Classification", 
                     command=apply_auto_classification, bg="lightgreen").pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
            # Initial preview
            dialog.after(100, preview_classifications)
            
        except ImportError as e:
            messagebox.showerror("Error", f"Auto-classification not available: {e}\\nPlease ensure auto_classify.py is present.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open auto-classification: {e}")

    def prev_page(self):
        """Go to previous page of uncategorized transactions"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_uncategorized_queue()

    def next_page(self):
        """Go to next page of uncategorized transactions"""
        total_count = self.logic.get_uncategorized_count()
        max_pages = (total_count + self.items_per_page - 1) // self.items_per_page
        if self.current_page < max_pages - 1:
            self.current_page += 1
            self.refresh_uncategorized_queue()

    def load_budget_grid(self):
        """Load budget data into the grid for the selected year"""
        try:
            year = int(self.budget_year.get())
            
            # Clear existing data
            for item in self.budget_tree.get_children():
                self.budget_tree.delete(item)
            
            # Get all categories and their yearly budgets
            categories = self.logic.get_categories()
            for category in categories:
                budget_amount = self.logic.get_budget(category, year)
                # Insert category row
                self.budget_tree.insert("", tk.END, values=(category, f"{budget_amount:.2f}"))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load budget grid: {e}")
    
    def add_new_category_row(self):
        """Add a new category by prompting user and adding to grid"""
        category_name = tk.simpledialog.askstring(
            "Add Category", 
            "Enter new category name:"
        )
        
        if category_name and category_name.strip():
            category_name = category_name.strip()
            try:
                # Add to database
                self.logic.add_category(category_name)
                
                # Add to grid with 0 budget
                year = int(self.budget_year.get())
                self.budget_tree.insert("", tk.END, values=(category_name, "0.00"))
                
                messagebox.showinfo("Success", f"Category '{category_name}' added!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {e}")
    
    def remove_selected_category(self):
        """Remove the selected category from both grid and database"""
        selection = self.budget_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a category to remove.")
            return
            
        item = selection[0]
        values = self.budget_tree.item(item, "values")
        category_name = values[0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm", f"Remove category '{category_name}'?\nThis will also remove all associated transactions and budgets."):
            try:
                # Remove from database
                self.logic.remove_category(category_name)
                
                # Remove from grid
                self.budget_tree.delete(item)
                
                messagebox.showinfo("Success", f"Category '{category_name}' removed!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove category: {e}")
    
    def refresh_categories(self):
        """Refresh the budget grid (replaces old category list refresh)"""
        if hasattr(self, 'budget_tree'):
            self.load_budget_grid()
            
    def edit_budget_cell(self, event):
        """Handle double-click to edit yearly budget amount"""
        selection = self.budget_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        column = self.budget_tree.identify_column(event.x)
        
        # Only allow editing the budget amount column (column #2)
        if column == "#2":
            # Get current values
            values = self.budget_tree.item(item, "values")
            category = values[0]
            current_amount = values[1]
            
            # Create edit dialog
            new_amount = tk.simpledialog.askfloat(
                "Edit Yearly Budget", 
                f"Enter yearly budget amount for {category}:\n(This will apply to all months in the year)",
                initialvalue=float(current_amount) if current_amount != "0.00" else 0.0,
                minvalue=0.0
            )
            
            if new_amount is not None:
                try:
                    year = int(self.budget_year.get())
                    
                    # Update in database (no month parameter needed)
                    self.logic.set_budget(category, year, new_amount)
                    
                    # Update display
                    self.budget_tree.item(item, values=(category, f"{new_amount:.2f}"))
                    
                    messagebox.showinfo("Success", f"Yearly budget for {category} updated!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update budget: {e}")

    def set_budget(self):
        """Legacy method - now handled by edit_budget_cell"""
        messagebox.showinfo("Info", "Double-click on a budget amount in the grid to edit it.")
    
    def edit_budget_cell(self, event):
        """Handle double-click to edit yearly budget amount"""
        item = self.budget_tree.selection()[0]
        column = self.budget_tree.identify_column(event.x)
        
        # Only allow editing the budget amount column (column #2)
        if column == "#2":
            # Get current values
            values = self.budget_tree.item(item, "values")
            category = values[0]
            current_amount = values[1]
            
            # Create edit dialog
            new_amount = tk.simpledialog.askfloat(
                "Edit Yearly Budget", 
                f"Enter yearly budget amount for {category}:\n(This will apply to all months in the year)",
                initialvalue=float(current_amount) if current_amount != "0.00" else 0.0,
                minvalue=0.0
            )
            
            if new_amount is not None:
                try:
                    year = int(self.budget_year.get())
                    
                    # Update in database (no month parameter needed)
                    self.logic.set_budget(category, year, new_amount)
                    
                    # Update display
                    self.budget_tree.item(item, values=(category, f"{new_amount:.2f}"))
                    
                    messagebox.showinfo("Success", f"Yearly budget for {category} updated!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update budget: {e}")
    
    def save_all_budgets(self):
        """Save all budget changes (in case of batch edits)"""
        try:
            # This method could be extended for batch operations
            # For now, budgets are saved immediately when edited
            messagebox.showinfo("Save", "All budgets are already saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save budgets: {e}")

    def set_budget(self):
        """Legacy method - now handled by edit_budget_cell"""
        messagebox.showinfo("Info", "Double-click on a budget amount in the grid to edit it.")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            try:
                imported_count = self.logic.import_csv(path)
                messagebox.showinfo("Import", f"CSV imported! {imported_count} transactions added to 'Uncategorized' category.")
                self.refresh_unclassified()
                # Refresh uncategorized queue if it exists
                if hasattr(self, 'uncategorized_tree'):
                    self.refresh_uncategorized_queue()
            except Exception as e:
                messagebox.showerror("Import Error", str(e))

    def refresh_unclassified(self):
        self.classify_list.delete(0, tk.END)
        for tx in self.logic.get_unclassified_transactions():
            self.classify_list.insert(tk.END, f"{tx[0]} | {tx[1]} | {tx[2]} | {tx[3]}")

    def classify_selected(self):
        sel = self.classify_list.curselection()
        if sel:
            tx_str = self.classify_list.get(sel[0])
            ver_nr = tx_str.split("|")[0].strip()
            
            # Get current categories for dropdown
            categories = self.logic.get_categories()
            if not categories:
                messagebox.showwarning("No Categories", "Please add categories in the Budgets tab first.")
                return
            
            # Create a simple dialog for category selection
            category_window = tk.Toplevel(self)
            category_window.title("Select Category")
            category_window.geometry("300x150")
            category_window.grab_set()  # Make it modal
            
            tk.Label(category_window, text=f"Select category for:\n{tx_str}").pack(pady=10)
            
            category_var = tk.StringVar(value=categories[0])
            category_dropdown = ttk.Combobox(category_window, textvariable=category_var, values=categories, state="readonly")
            category_dropdown.pack(pady=10)
            
            def on_classify():
                selected_cat = category_var.get()
                if selected_cat:
                    try:
                        self.logic.classify_transaction(ver_nr, selected_cat)
                        self.refresh_unclassified()
                        category_window.destroy()
                        messagebox.showinfo("Success", f"Transaction classified as '{selected_cat}'")
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
            
            def on_cancel():
                category_window.destroy()
            
            button_frame = tk.Frame(category_window)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Classify", command=on_classify).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

    def show_monthly_report(self):
        """Show spending vs yearly budget for a specific month"""
        try:
            year = int(self.report_year.get())
            month = int(self.report_month.get())
            report = self.logic.get_spending_report(year, month)
            
            # Clear existing data
            for i in self.report_tree.get_children():
                self.report_tree.delete(i)
            
            # Add data with percentage calculation
            for row in report:
                spent = row['spent']
                budget = row['budget']
                diff = row['diff']
                percent = f"{(spent/budget*100):.1f}%" if budget > 0 else "N/A"
                
                self.report_tree.insert("", tk.END, values=(
                    row['category'], 
                    f"{spent:.2f}", 
                    f"{budget:.2f}", 
                    f"{diff:.2f}",
                    percent
                ))
                
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def show_yearly_report(self):
        """Show spending vs yearly budget for entire year"""
        try:
            year = int(self.report_year.get())
            report = self.logic.get_yearly_spending_report(year)
            
            # Clear existing data
            for i in self.report_tree.get_children():
                self.report_tree.delete(i)
            
            # Add data with percentage calculation
            for row in report:
                spent = row['spent']
                budget = row['budget']
                diff = row['diff']
                percent = f"{(spent/budget*100):.1f}%" if budget > 0 else "N/A"
                
                self.report_tree.insert("", tk.END, values=(
                    row['category'], 
                    f"{spent:.2f}", 
                    f"{budget:.2f}", 
                    f"{diff:.2f}",
                    percent
                ))
                
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_report(self):
        """Legacy method - now defaults to monthly report"""
        self.show_monthly_report()

def prompt_password():
    root = tk.Tk()
    root.withdraw()
    pw = simpledialog.askstring("Password", "Enter database password:", show='*')
    root.destroy()
    return pw
