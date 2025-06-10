# LinkedInFinder

A powerful web scraping tool that automatically discovers and validates company executives' LinkedIn profiles from company websites.

## Highlights

- 🎯 **Intelligent Executive Detection**: Automatically identifies CEOs, CTOs, Founders, and other key executives from company websites
- 🔍 **Smart Name Recognition**: Uses Flair NER (Named Entity Recognition) to accurately identify person names
- 🔗 **LinkedIn Profile Matching**: Automatically finds and validates LinkedIn profiles for identified executives
- 📊 **Accuracy Validation**: Includes tools to validate scraped data against ground truth datasets
- 🌐 **Flexible Usage**: Supports both single company analysis and bulk processing modes

## Demo

The tool operates in two modes:

1. **Single Company Mode**: 
   - Input a company website URL and name
   - Get immediate results about executives and their LinkedIn profiles

2. **Bulk Testing Mode**:
   - Process multiple companies from a dataset
   - Automatically validate results against ground truth data
   - Get detailed accuracy statistics for each company

## Quick Start

1. **Setup**
   ```bash
   # Create a virtual environment
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   
   # Install dependencies
   pip install requests beautifulsoup4 serpapi flair pandas
   ```

2. **Configuration**
   - Get a SERP API key from [SerpApi](https://serpapi.com/)
   - Add your API key in the `main.py` file

3. **Usage**
   ```bash
   python main.py
   ```
   Then choose your mode:
   - Enter '1' for single company analysis
   - Enter '2' for bulk testing using dataset.csv

4. **Dataset Format**
   For bulk testing, prepare a CSV file with the following columns:
   - Company: Company name
   - Domain: Company website URL
   - Full Name: Executive's full name
   - Title: Executive's title
   - LinkedIn Profile: LinkedIn profile URL

## Note
This tool respects website scraping policies and includes appropriate delays between requests. Please ensure you have permission to scrape target websites and comply with LinkedIn's terms of service. 