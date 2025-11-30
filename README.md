# GPAI Model Documentation Dashboard

A transparency dashboard for General-Purpose AI (GPAI) models, tracking compliance with the EU AI Act requirements. This project scrapes official documentation from AI providers and presents it in an accessible, searchable interface.

## Overview

This dashboard helps track and visualise GPAI model documentation transparency across major AI providers. It evaluates models against the EU AI Act's documentation requirements and presents the information through an intuitive web interface.

### Live Demo
🌐 https://eziozoani.github.io/gpai-model-form/

### Key Features
- **Automated Documentation Scraping**: Collects model information from official sources
- **Transparency Scoring**: Evaluates documentation completeness across 8 key sections
- **Visual Dashboard**: Traffic light system (red/amber/green) for quick assessment
- **Source Attribution**: Full provenance tracking with confidence scores
- **EU Code of Practice Tracking**: Identifies signatories and compliance status
- **Advanced Filtering**: By provider, region, size, and transparency score
- **Detailed Documentation View**: Full text with source attribution

## Repository Structure

```
gpai-model-docs/
├── site/                    # React frontend application
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   │   ├── ModelGrid.tsx        # Main grid view
│   │   │   ├── ModelDetailPanel.tsx # Detailed model view
│   │   │   └── Heatmap.tsx          # Visual heatmap
│   │   ├── data/           # Static configuration
│   │   └── types/          # TypeScript definitions
│   ├── public/             # Static assets
│   ├── data/               # JSON data files (generated)
│   └── dist/               # Build output for GitHub Pages
│
├── scripts/                 # Python backend scrapers
│   ├── crawl.py            # Main scraper for official sources
│   ├── crawl_general.py    # Gap-filling scraper
│   ├── db.py               # SQLite database operations
│   ├── db_export.py        # Export to JSON for frontend
│   ├── evaluate.py         # Data quality evaluation
│   ├── scoring.py          # Transparency scoring logic
│   ├── text_extraction.py  # NLP content validation
│   ├── sync_data.sh        # Sync data to React app
│   └── test_scrapers.sh    # Test scraping pipeline
│
├── data/                    # *test Local data storage*
│   ├── model_docs.db       # SQLite database (local only)
│   └── models/             # Individual model JSON exports
│
├── config/                  # Configuration files
│   └── sources.yaml        # Scraper source definitions
│
├── .github/                 # GitHub Actions workflows
│   └── workflows/
│       └── deploy.yml      # Auto-deploy to GitHub Pages
│
└── requirements.txt         # Python dependencies
```

##  Getting Started

### Prerequisites
- Python 3.10+
- Node.js 16+
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/EziOzoani/gpai-model-form.git
   cd gpai-model-form
   ```

2. **Set up Python environment** (for data collection)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the complete data pipeline**
   ```bash
   ./scripts/test_scrapers.sh
   ```
   This will:
   - Initialise the database
   - Scrape official sources
   - Run gap-filling scrapers
   - Evaluate data quality
   - Export to JSON
   - Sync to React app

4. **Start the React development server**
   ```bash
   cd site
   npm install
   npm run dev
   ```

5. **Open in browser**
   Navigate to http://localhost:5173

### Production Deployment

The site auto-deploys to GitHub Pages when you push to main:

```bash
# Build the React app
cd site
npm run build

# The dist folder is created with production build
# Commit and push all changes
git add .
git commit -m "Update model data and build"
git push origin main
```

## Evaluation Framework

### Documentation Sections

The dashboard evaluates AI models across 8 documentation sections required/recommended by the EU AI Act:

#### Core Sections (Required)
1. **General Information** 
   - Legal entity name
   - Model identifier
   - Release dates (global and EU market)
   
2. **Model Properties**
   - Architecture details
   - Input/output modalities
   - Parameter counts
   
3. **Distribution & Licensing**
   - Available channels
   - License types
   - Terms of service
   
4. **Intended Use**
   - Use cases and applications
   - Integration requirements
   - Restrictions and limitations
   
5. **Training Data**
   - Data sources and types
   - Selection criteria
   - Bias mitigation measures

#### Bonus Sections (Enhanced transparency) ⭐
6. **Training Process**
   - Methodology and techniques
   - Decision rationale
   - Training infrastructure
   
7. **Computational Requirements**
   - Hardware specifications
   - Training duration
   - FLOPs calculations
   
8. **Energy Consumption**
   - Power usage (MWh)
   - Carbon footprint
   - Efficiency measures

### Scoring Methodology

- **Field Completeness**: Each field within a section is scored 0 or 1
- **Section Score**: Percentage of fields completed in that section
- **Overall Score**: Weighted average across all sections
- **Visualisation**:
  - 🔴 Red (0-33%): Critical gaps
  - 🟡 Amber (34-66%): Partial documentation
  - 🟢 Green (67-100%): Comprehensive documentation
  - ⭐ Star: Bonus section completed

### Source Confidence Levels

All scraped data includes confidence scores:
- **100%**: Official API responses
- **95%**: Official documentation sites
- **90%**: Official announcements/blogs
- **85%**: HuggingFace model cards
- **80%**: ArXiv papers
- **60-75%**: Third-party technical sites

## 🤖 Currently Tracked Providers

- **Google** (Gemini family) - 4 models
- **Anthropic** (Claude family) - In development
- **OpenAI** (GPT family) - Access restricted
- **Mistral AI** (Mistral/Mixtral) - 5 models
- **Meta** (Llama family) - In development
- **Cohere** (Command family) - 6 models

## 🔄 Data Management

### Manual Data Updates

```bash
# Full pipeline
./scripts/test_scrapers.sh

# Individual components
python scripts/crawl.py          # Official sources only
python scripts/crawl_general.py  # Gap-filling from other sources
python scripts/evaluate.py       # Generate quality report
python scripts/db_export.py      # Export to JSON
./scripts/sync_data.sh          # Copy to React app
```

### Automated Updates

A GitHub Actions workflow can be configured for quarterly updates:
- Runs scrapers on schedule
- Commits updated JSON files
- Triggers rebuild and deployment

## 🛠️ Technical Architecture

### Frontend Stack
- **React 18** with TypeScript
- **Vite** for fast builds
- **Tailwind CSS** for styling
- **Shadcn/UI** component library
- **Recharts** for data visualisation

### Backend Stack
- **Python 3.10+** 
- **BeautifulSoup4** for HTML parsing
- **SQLite** for local data storage
- **Custom NLP** for content validation

### Deployment
- **GitHub Pages** for hosting
- **GitHub Actions** for CI/CD
- **JSON** data files (no backend required)

## Roadmap

### Near Term
- [ ] Add historical tracking
- [ ] Implement automated quarterly updates
- [ ] Add CSV export functionality

### Long Term
- [ ] Multi-language support
- [ ] Inetgrate with map
- [ ] Real-time update notifications

## 📝 TODO for GCP Deployment

### Feedback System
- [ ] Add necessary keys on GCP for feedback to GitHub issues creation:
  - Store GitHub Personal Access Token in GCP Secret Manager or as environment variable
  - Configure API endpoint to handle feedback submissions
  - Update frontend to use GCP backend API instead of direct GitHub calls




## 🙏 Acknowledgments

- EU AI Office codes of practice [model documentation form](https://code-of-practice.ai/?section=summary)


---

**Disclaimer**: This tool aids transparency assessment but does not constitute legal compliance verification. Consult official EU AI Act documentation and legal advisors for compliance matters.
