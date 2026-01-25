# Jupyter Notebook Feature Guide

## Overview
The platform supports uploading and rendering Jupyter Notebooks (.ipynb files) as course content, with integration for Google Colab editing.

## How It Works

### For Course Creators (Uploading Notebooks)

#### Method 1: Upload File
1. Go to Course Management → Curriculum
2. Add Content → Select "Jupyter Notebook"
3. Choose "Upload File"
4. Select your `.ipynb` file
5. Toggle "Enable Open in Colab" (recommended: ON)
6. Click "Add Item"

#### Method 2: Import from URL (✨ EASIEST for Colab Notebooks!)
1. Go to Course Management → Curriculum
2. Add Content → Select "Jupyter Notebook"
3. Choose "Import from URL"
4. Paste the URL (see supported types below)

**Supported URL Types:**

**⚡ FASTEST: Google Colab URL (Direct - NEW!)**
1. Open your notebook in Google Colab
2. Make sure it's saved (File → Save)
3. Copy the URL from your browser address bar
4. Paste it into the platform
5. ⚡ System automatically extracts the Drive file ID!

**Example Colab URLs (all work):**
- `https://colab.research.google.com/drive/1IvU0YI2kRCO1q3W96Kox5CAz1f9dzUqW`
- `https://colab.research.google.com/drive/1abc123...xyz?usp=drive_link`

**🚀 ALSO WORKS: Google Drive Sharing Link**
1. File → **Locate in Drive** (opens the file in Google Drive)
2. In Google Drive, right-click the `.ipynb` file → **Get link**
3. Set sharing to **"Anyone with the link"** can view
4. Copy and paste the sharing link
5. ✨ The system automatically converts it to a direct download link!

**Example Google Drive URLs (all work):**
- `https://drive.google.com/file/d/1abc123...xyz/view`
- `https://drive.google.com/open?id=1abc123...xyz`

**Also Supported:**
- ✅ **GitHub URLs**: Both regular and raw URLs work
  - Regular: `https://github.com/user/repo/blob/main/notebook.ipynb`
  - Raw: `https://raw.githubusercontent.com/user/repo/main/notebook.ipynb`
  - System auto-converts regular to raw!
- ✅ **GitHub Gist**: `https://gist.github.com/username/gist_id`
- ✅ **Public cloud storage**: Google Cloud Storage, AWS S3, etc.
- ✅ **Any direct `.ipynb` URL**

**❌ NOT Supported:**
- Colab **system example** notebooks: `https://colab.research.google.com/notebooks/...`
  - These are Google's built-in examples, not in your Drive
  - Solution: Save a copy to your Drive first, then use the new Colab URL

**Example GitHub Workflow:**
```bash
# 1. Save notebook to your repo
git add my_notebook.ipynb
git commit -m "Add notebook"
git push

# 2. Get the raw URL
# Go to GitHub → Click the file → Click "Raw" button
# Copy URL: https://raw.githubusercontent.com/username/repo/main/my_notebook.ipynb
```

### For Students (Viewing and Using Notebooks)

#### Viewing Notebooks
- Notebooks are rendered directly in the course player
- All cells are visible: code cells, markdown, outputs
- Syntax highlighting for code
- Read-only mode (no execution in the platform)

#### Using with Google Colab
When students click "Open in Colab":
1. The notebook is automatically downloaded
2. Instructions appear to upload to Colab
3. Google Colab opens in a new tab
4. Student uploads the downloaded file
5. Student can now run and edit the notebook interactively

**Why this workflow?**
- Uploaded notebooks are stored on our backend (may require authentication)
- Google Colab cannot fetch authenticated/private URLs
- Downloading + uploading ensures it works for all notebooks

**Exception: Public GitHub Notebooks**
If the notebook was imported from a public GitHub raw URL, the "Open in Colab" button will open it directly in Colab without downloading (seamless experience).

## Technical Details

### Backend
- **Validation**: Uses `nbformat` library to validate .ipynb structure
- **Metadata Extraction**:
  - Cell count
  - Programming language
  - Kernel name
  - Whether outputs are present
- **Storage**: Notebooks stored as files (like other course content)

### Frontend
- **Rendering**: Uses `react-ipynb-renderer` library
- **Features**:
  - Syntax highlighting (Monokai theme)
  - Metadata badges
  - Download button (always works)
  - Open in Colab button (with smart fallback)

## Limitations & Known Issues

1. **Colab Integration**:
   - Cannot open private/authenticated notebooks directly in Colab
   - Requires download → upload workflow for most cases
   - Public GitHub URLs work seamlessly

2. **URL Import**:
   - URL must be publicly accessible (no auth)
   - Must be direct link to `.ipynb` file (not a viewer page)
   - Colab viewer URLs don't work

3. **File Size**:
   - Large notebooks (100+ MB) may be slow to render
   - Consider file size limits on your backend

## Best Practices

### For Course Creators
1. **Test Your Notebooks**: Before uploading, ensure they run in a fresh Colab environment
2. **Include Outputs**: Running cells before saving makes notebooks more informative for students
3. **Use GitHub**: If you frequently update notebooks, host them on GitHub and use URL import
4. **Enable Colab**: Always enable the Colab button unless you have a specific reason not to

### For Students
1. **Download First**: If you want to keep your changes, download the notebook before editing
2. **Use Colab for Execution**: The platform is for viewing; use Colab for running code
3. **Save Your Work**: Remember to save your Colab notebooks to your Google Drive

## Example Workflows

### Workflow 1: Direct Colab URL (FASTEST! ⚡ NEW!)

**For any notebook already open in Colab:**
1. Make sure your notebook is saved (File → Save or Ctrl+S)
2. Copy the URL from your browser address bar
   - Example: `https://colab.research.google.com/drive/1IvU0YI2kRCO1q3W96Kox5CAz1f9dzUqW`
3. Go to your course platform → Add Content → Jupyter Notebook
4. Choose "Import from URL"
5. Paste the Colab URL
6. You'll see: "✓ Google Colab link detected - extracting Drive file ID automatically"
7. Click "Add Item"
8. ⚡ Done! (~15 seconds total)

**Just copy-paste the URL you're already viewing!**

### Workflow 2: Google's Example Notebooks (like TPU notebook)

**For system example notebooks like `https://colab.research.google.com/notebooks/tpu.ipynb`:**
1. Open the example notebook in Colab
2. File → **Save a copy in Drive**
3. The copy opens automatically with a new URL like: `https://colab.research.google.com/drive/1abc...`
4. Copy that new URL from your browser
5. Paste into course platform (Import from URL)
6. ✨ Done!

**OR use the Drive sharing link method:**
1. After saving copy, File → **Locate in Drive**
2. Right-click the file → **Get link** → Set to "Anyone with the link"
3. Paste that Drive link into course platform
4. ✨ Done!

### Workflow 2: GitHub Repository
1. Create a notebook or get one you want to share
2. Push to GitHub:
```bash
git add my_notebook.ipynb
git commit -m "Add notebook"
git push
```
3. Get the URL (either works):
   - Regular: `https://github.com/user/repo/blob/main/my_notebook.ipynb`
   - Raw: `https://raw.githubusercontent.com/user/repo/main/my_notebook.ipynb`
4. Paste into the URL field
5. System auto-converts to raw URL if needed

### Workflow 3: Traditional Upload
1. Download the `.ipynb` file
2. Use "Upload File" method
3. Select the file
4. Upload complete!

## Troubleshooting

### "Failed to fetch notebook from URL"
- Ensure URL is publicly accessible (try opening in incognito browser)
- Check that URL points to `.ipynb` file, not a viewer page
- Verify the URL returns JSON, not HTML

### "Invalid notebook file"
- Ensure file is valid `.ipynb` format
- Try opening in Jupyter/Colab first to verify it's not corrupted
- Check that all cells are properly formatted

### "Open in Colab" not working
- This is expected for private URLs
- Use the download workflow (automatic)
- For public GitHub notebooks, ensure you're using the raw URL

## Future Enhancements (Potential)

- [ ] In-browser notebook execution (using Pyodide)
- [ ] Automatic GitHub integration for course creators
- [ ] Notebook version tracking
- [ ] Student notebook submissions (for assignments)
- [ ] Embedded Colab frames (if feasible)
