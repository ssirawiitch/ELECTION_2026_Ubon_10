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
├── README.md                      # Project documentation
│
├── data-final/                    # Final processed datasets
│   ├── data.json                  # Final election data
│   ├── candidate_mapping_color.json
│   ├── party_list_mapping.json
│   ├── election_locations_66.csv
│   └── election_scores_2566.csv
│
├── data-processed/                # Processed analysis outputs by stage
│   ├── 1/                         # Data preparation & aggregation
│   │   ├── candidate_mapping.csv
│   │   ├── party_mapping.csv
│   │   ├── constituency_by_amphoe.csv
│   │   ├── constituency_by_tambon.csv
│   │   ├── constituency_station.csv
│   │   ├── partylist_by_amphoe.csv
│   │   ├── partylist_station.csv
│   │   └── votes_per_station.csv
│   ├── 2/                         # Constituency-level analysis
│   │   ├── const_margin_amphoe.csv
│   │   ├── const_overall.csv
│   │   ├── const_winner_amphoe.csv
│   │   ├── const_winner_tambon.csv
│   │   └── constituency_by_amphoe.csv
│   ├── 3/                         # Split-ticket analysis
│   │   ├── partylist_overall.csv
│   │   ├── split_ticket_group_a.csv
│   │   └── split_ticket_group_b.csv
│   ├── 4/                         # Advance vs election day voting
│   │   ├── advance_vs_ed_constituency.csv
│   │   └── advance_vs_ed_partylist.csv
│   ├── 5/                         # Geographic concentration analysis
│   │   ├── geo_concentration.csv
│   │   ├── geo_margin_tambon.csv
│   │   └── geo_winner_tambon.csv
│   ├── 6/                         # Swing analysis (2566 vs 2569)
│   │   ├── swing_amphoe_2566_2569.csv
│   │   ├── swing_constituency_2566_2569.csv
│   │   └── swing_partylist_2566_2569.csv
│   └── 7/                         # Border region analysis
│       ├── border_amphoe_summary.csv
│       ├── border_events_timeline.csv
│       ├── border_party21_share.csv
│       ├── border_tambon_detail.csv
│       ├── border_vs_inland_constituency.csv
│       └── border_vs_inland_partylist.csv
│
├── ds/                            # Jupyter notebooks for analysis
│   ├── 01_data_prep.ipynb         # Data preparation & cleaning
│   ├── 02_const_analysis.ipynb    # Constituency-level analysis
│   ├── 03_split-ticket_analysis.ipynb  # Split-ticket voting patterns
│   ├── 04_advance_vs_election_day.ipynb # Advance vs election day comparison
│   ├── 05_geographic_Concentration.ipynb # Geographic concentration metrics
│   ├── 06_comparison_66_69.ipynb  # Comparison with previous elections
│   └── 07_border_events_overlay.ipynb    # Border region & events analysis
│
├── figures/                       # Output visualizations & plots
│
├── ocr/                           # OCR pipeline and quality assurance
│   ├── clean/                     # Manual verification scripts
│   │   ├── apply_corrections.py
│   │   ├── check_luangna.py
│   │   ├── dump_stations.py
│   │   ├── inspect_entry.py
│   │   ├── inspect_stations.py
│   │   ├── main.py
│   │   ├── review_1digit.py
│   │   ├── review_2digit.py
│   │   ├── review_high_score.py
│   │   └── verify_images.py
│   │
│   ├── model_ocr/                 # OCR processing pipeline
│   │   ├── run_score_ocr.py       # Main OCR execution script
│   │   └── score_ocr/             # Qwen + Typhon OCR models
│   │
│   ├── scrap/                     # YOLO PDF scraping
│   │   ├── export_yolo_score_crops.py
│   │   ├── models/                # YOLO model files
│   │   └── src/                   # Supporting utilities
│   │
│   └── ui/                        # Manual verification interface
│       └── review_ui.py           # Streamlit dashboard for labeling
│
├── visualize/                     # Visualization and mapping
│   ├── map.py                     # Election map generation
│   ├── find_ubon.py               # Utility for Ubon data
│   ├── election_map_ubon10.html   # Interactive election map
│   └── ubon_map.geojson           # Geospatial boundaries
│
├── yolo_score_crops/              # YOLO extracted score images
│   └── yolo_score_crops/          # Image crops by voting unit
│
└── เขต 10/                        # Raw election documents
    ├── ล่วงหน้านอกเขตเลือกตั้งและนอกราชอาณาจักร/ # Advance voting
    ├── อำเภอเดชอุดม/              # Deechudom District
    ├── อำเภอทุ่งศรีอุดม/          # Tungsriudom District
    ├── อำเภอน้ำขุ่น/              # Namkhuen District
    ├── อำเภอน้ำยืน/               # Namyeun District
    └── อำเภอสำโรง/                # Samrong District
```

### Key Components

#### `data-final/`
Final processed and consolidated election datasets:
- Complete election results with all voting units
- Party and candidate mappings with color codes
- Election location and scoring data

#### `data-processed/`
Staged analysis outputs organized by analysis type:
- **Stage 1**: Data preparation and aggregation by administrative levels
- **Stage 2**: Constituency-level voting patterns and margins
- **Stage 3**: Split-ticket voting analysis
- **Stage 4**: Advance vs. election day voting comparison
- **Stage 5**: Geographic concentration and regional analysis
- **Stage 6**: Swing analysis comparing 2566 and 2569 elections
- **Stage 7**: Border region vs. inland analysis with event timeline

#### `ds/` (Jupyter Notebooks)
Analysis notebooks corresponding to data-processed stages:
- **01_data_prep**: Data loading, cleaning, and aggregation
- **02_const_analysis**: Constituency voting patterns and competition
- **03_split-ticket_analysis**: Voter behavior in constituency vs. party-list voting
- **04_advance_vs_election_day**: Temporal voting patterns
- **05_geographic_Concentration**: Regional voting concentration and patterns
- **06_comparison_66_69**: Historical comparison with previous election cycles
- **07_border_events_overlay**: Border security events and voting correlation

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
- Detects score sections using YOLO object detection
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

#### `เขต 10/` (Thai District 10)
Raw election documents organized by district (Amphoe) and voting method:
- Advance voting data (ล่วงหน้า)
- Per-district subdirectories for each Amphoe in District 10

