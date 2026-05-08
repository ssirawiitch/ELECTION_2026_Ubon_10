# Thailand 2026 Election Data Science Project
## Ubon Ratchathani Province - District 10 Analysis

### Overview
This project aims to extract, process, and analyze election data from Thailand's 2026 general election held in Ubon Ratchathani Province, District 10. The project focuses on converting hand-written PDF election forms into structured digital data for statistical analysis and insights.

### Data Source
- **Source**: Thai Election Commission (Thai Chamber)
- **Link**: https://drive.google.com/drive/folders/1jTnfyPKpXbHr72OAyIScWOaeL8vdrF1X
- **Format**: PDF documents

### Data Challenges
The election forms present significant data quality challenges:
- Hand-written entries with mixed Thai and Arabic numerals
- Tilted or unclear images
- Missing or incomplete data on some pages
- Poor OCR readability when scanning entire PDF pages

### Methodology

#### 1. **Image Extraction (YOLO Scraping)**
- Used YOLO (You Only Look Once) object detection to automatically extract score sections from PDF files
- Cropped only the relevant scoring areas to reduce noise and improve OCR accuracy
- Converted PDFs into high-quality image crops

#### 2. **Optical Character Recognition (OCR)**
- Applied dual-model OCR approach for robust reading:
  - **Qwen**: For Thai text and numeral recognition
  - **Typhon**: For cross-validation and error checking
- Models validate each other's outputs to improve accuracy

#### 3. **Manual Verification & Quality Assurance**
Implemented a three-tier verification system:

1. **High-Impact Values**: All entries with scores > 500 (manually verified)
   - These have the most impact if incorrect
   
2. **Two-Digit Numbers**: 100% manual verification
   
3. **Stratified Sampling**:
   - Units digit 0: 20% random sample
   - Other digits: Equal proportional sampling
   - **Total**: 6,000 out of 18,000 entries manually verified (33% coverage)

4. **Critical Data**: Top 2 candidates across all 305 voting units
   - 100% manual verification
   - Essential for accurate election outcome analysis

#### 4. **Data Compilation**
- All verified data consolidated into a single JSON file
- Passed to downstream analysis pipeline

### Project Structure

```
DS_Election_2026/
├── data-final/
│   ├── data.json                 # Final processed election data
│   └── candidate_mapping_color.json
│
├── ocr/
│   ├── clean/                    # Manual verification scripts
│   │   ├── apply_corrections.py
│   │   ├── check_luangna.py
│   │   ├── inspect_entry.py
│   │   ├── inspect_stations.py
│   │   ├── review_1digit.py
│   │   ├── review_2digit.py
│   │   ├── review_high_score.py
│   │   └── verify_images.py
│   │
│   ├── model_ocr/
│   │   └── model_ocr.py          # Qwen + Typhon OCR pipeline
│   │
│   ├── scrap/
│   │   └── crop_pdf.py           # YOLO-based PDF scraping
│   │
│   └── ui/
│       └── review_ui.py          # Streamlit dashboard for manual labeling
│
├── model/                         # Model development and analysis
│
├── visualize/
│   ├── map.py                    # Election map visualization
│   ├── find_ubon.py
│   ├── election_map_ubon10.html
│   └── ubon_map.geojson
│
└── yolo_score_crops/             # YOLO extracted score images
```

### Key Components

#### `ocr/clean/`
Scripts for sampling and manual verification of OCR results:
- Random stratified sampling from OCR output
- Data entry verification interface
- Quality assurance checks

#### `ocr/model_ocr/`
OCR processing pipeline:
- Loads cropped score images
- Passes through Qwen and Typhon models
- Cross-validates model outputs
- Flags discrepancies for manual review

#### `ocr/scrap/`
PDF processing:
- Detects score sections using YOLO
- Crops relevant areas from PDF pages
- Exports high-quality images for OCR

#### `ocr/ui/`
Streamlit-based dashboard:
- Manual data entry interface
- Verification of model predictions
- Flag ambiguous or unclear entries
- Real-time accuracy tracking

#### `visualize/`
Data analysis and visualization:
- Geospatial mapping of election results
- Statistical insights and trends
- Interactive visualizations of vote distribution

