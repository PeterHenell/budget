# CSV Import Functionality

## Overview
The budget app now includes a command-line import utility that processes CSV files from the `input` folder. **All imported transactions are automatically placed in an "Uncategorized" category**, creating a queue for later classification through the GUI.

## New Workflow

### 1. Bulk Import (Recommended)
```bash
make import
```
- All transactions imported to "Uncategorized" category
- No immediate classification required
- Files automatically archived after import
- Use GUI to classify transactions at your convenience

### 2. Optional Interactive Classification
- During import, you can choose to classify some transactions immediately
- Or skip and classify everything later in the GUI

## How to Use

### 1. Setup
```bash
make install
```

### 2. Place CSV Files
Put your CSV files in the `input/` folder.

### 3. Run the Import
```bash
make import
```

### 4. Import Process
The script will:
1. Ask for your database password
2. Import all transactions to "Uncategorized" category
3. Optionally allow immediate classification of some transactions
4. Archive processed files to `archive/` folder

### 5. GUI Classification (New!)
Use the **"Uncategorized Queue"** tab in the GUI for easy classification:

#### Features:
- **View all uncategorized transactions** with pagination
- **Single transaction classification**: Select and classify one at a time
- **Multi-select classification**: Hold Ctrl and classify multiple transactions
- **Batch classification by keywords**: Automatically classify based on description patterns
- **Real-time count updates**: See remaining uncategorized transactions
- **Advanced filtering**: Smart keyword matching with preview

#### Batch Classification Example:
- Keywords: `GROCERY, STORE, SUPERMARKET`
- Category: `Mat`
- All matching transactions automatically classified

## GUI Features

### Uncategorized Queue Tab
- **Transaction List**: Paginated view with date, description, and amount
- **Category Dropdown**: Quick selection from available categories
- **Classify Selected**: Single transaction classification
- **Classify Multiple**: Bulk classification for selected transactions
- **Batch Classify**: Smart keyword-based automatic classification
- **Pagination**: Handle large numbers of transactions efficiently

### Benefits of New System
✅ **Bulk Import**: Import entire CSV files without manual classification
✅ **Queue System**: All transactions safely stored in "Uncategorized"
✅ **Flexible Classification**: Classify at your own pace using the GUI
✅ **Batch Processing**: Smart keyword-based classification
✅ **Multi-Select**: Classify multiple transactions at once
✅ **No Data Loss**: No transactions left truly unclassified

## CSV Format
The CSV files should have Swedish headers:
- Bokföringsdatum (Booking date)
- Verifikationsnummer (Verification number)
- Text (Description)
- Belopp (Amount)
- And optionally: Valutadatum, Saldo

## Example Workflows

### Quick Import
1. Put CSV in `input/` folder
2. Run `make import`
3. Enter password
4. Choose "n" for immediate classification
5. Use GUI later to classify at leisure

### Immediate Classification
1. Put CSV in `input/` folder
2. Run `make import` 
3. Enter password
4. Choose "y" for immediate classification
5. Classify transactions interactively
6. Finish remaining in GUI

### Batch Classification in GUI
1. Import transactions (they go to "Uncategorized")
2. Open GUI → "Uncategorized Queue" tab
3. Click "Batch Classify"
4. Enter keywords like: `GROCERY, STORE, ICA, COOP`
5. Select category: `Mat`
6. Preview matches → Apply
7. Repeat for other patterns

## Command Line vs GUI
- **Command Line**: Good for immediate classification of small batches
- **GUI**: Better for batch operations, visual review, and complex classification patterns
- **Combined**: Import via CLI, classify via GUI (recommended)
