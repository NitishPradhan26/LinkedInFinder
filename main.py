import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from urllib.parse import urljoin
from serpapi import GoogleSearch  # Import the SERP API client
from flair.data import Sentence
from flair.models import SequenceTagger
import pandas as pd
from difflib import SequenceMatcher
from urllib.parse import urlparse
import re


class CompanyWebScraper:
    def __init__(self, serp_api_key: str):
        self.title_keywords = ['CEO', 'CTO', 'Founder', 'Co-Founder', 'Chief Technology Officer', 'Chief Executive Officer', 'Co-Founders']
        self.max_distance = 3
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.tagger = SequenceTagger.load('flair/ner-english')
        self.serp_api_key = serp_api_key
        
    def get_website_content(self, domain: str, company_name: str) -> List[Dict]:
        """Main function to scrape website and find people"""
        # Common paths where executive info might be found
        common_paths = [
            '/about', 
            '/team', 
            '/about-us', 
            '/leadership', 
            '/management',
            '/company',
            '/our-team',
            '/company/paraform',
            '/team.html',
            '/home/company/about',
            '/our-mission',
            '/about/leadership-team',
            '/about-actuate'
        ]
        
        found_people = []
        
        # Try each common path
        for path in common_paths:
            try:
                url = urljoin(domain, path)
                print(f"Checking {url}")
                
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    people = self.extract_people_info(response.text, company_name)
                    found_people.extend(people)
            except Exception as e:
                print(f"Error checking {path}: {e}")
                continue
        
        return self.remove_duplicates(found_people)

    def is_likely_name(self, text: str) -> bool:
        """Use Flair to check if text is likely a person's name"""
        print("\n--- is_likely_name Debug ---")
        print(f"Input text length: {len(text)}")
        print(f"First 50 chars: {text[:50]}...")
        
        # First check basic word count
        words = text.strip().split()
        print(f"Word count: {len(words)}")
        
        if not (1 <= len(words) <= 10):
            print("Rejected: Too many words")
            return False
        
        try:
            # Take only first 10 words and limit total character length
            limited_text = ' '.join(words[:10])[:100]  # Also limit total characters
            print(f"Limited text: {limited_text}")
            
            # Process with Flair
            sentence = Sentence(limited_text)
            self.tagger.predict(sentence)
            
            # Check results
            entities = sentence.get_spans('ner')
            print(f"Found entities: {[f'{e.text} ({e.tag})' for e in entities]}")
            
            is_person = any(entity.tag == 'PER' for entity in entities)
            print(f"Is person: {is_person}")
            return is_person
            
        except Exception as e:
            print(f"Error in Flair processing: {str(e)}")
            # Fallback to simple word count check if Flair fails
            return 1 <= len(words) <= 3
    
    def find_name_in_text(self, text: str, title: str) -> Optional[str]:
        """Find name in text using spaCy NER"""
        words = text.split()
        
        # Find the index of the title
        title_index = -1
        for i, word in enumerate(words):
            if word.lower() == title.lower():
                title_index = i
                break
                
        if title_index == -1:
            return None
                
        # Look at words before the title (up to 3 words)
        start_index = max(0, title_index - 3)
        before_words = words[start_index:title_index]
        
        print("\nLooking at words before title:")
        for word in before_words:
            print(f"\nChecking word: {word}")
            sentence = Sentence(word)
            self.tagger.predict(sentence)
            
            print("Entities found:")
            for entity in sentence.get_spans('ner'):
                print(f"Text: {entity.text}, Label: {entity.tag}")
                
            if sentence.get_spans('ner') and any(entity.tag == 'PER' for entity in sentence.get_spans('ner')):
                return word
        
        # Look at words after the title (up to 3 words)
        end_index = min(len(words), title_index + 4)
        after_words = words[title_index + 1:end_index]
        
        print("\nLooking at words after title:")
        for word in after_words:
            print(f"\nChecking word: {word}")
            sentence = Sentence(word)
            self.tagger.predict(sentence)
            
            print("Entities found:")
            for entity in sentence.get_spans('ner'):
                print(f"Text: {entity.text}, Label: {entity.tag}")
                
            if sentence.get_spans('ner') and any(entity.tag == 'PER' for entity in sentence.get_spans('ner')):
                return word
        
        return None
    
    def find_name_near_title(self, title_element, max_distance: int = 4) -> Optional[str]:
        """Find name by looking up and down from the title element"""
        def check_element_for_name(element) -> Optional[str]:
            if element and element.text:
                text = element.text.strip()
                print(" Check_element_for_name: this is the text", text)
                if self.is_likely_name(text):
                    return text
            return None
        
        def check_element_and_children(element) -> Optional[str]:
            # Check the element itself
            print("This is the siblingelement tag", element.name)
            name = check_element_for_name(element)
            if name:
                print(" this is the name", name)
                return name
            
            # Recursively check all children
            for child in element.find_all(recursive=True):
                name = check_element_for_name(child)
                if name:
                    print(" this is the name", name)
                    return name
            return None
        
        # Look up through previous elements
        current = title_element
        distance = 0
        while current and distance < max_distance:
            # Check previous sibling and all its descendants
            print("This is the current element tag", current.name)
            prev_sibling = current.find_previous_sibling()
            if prev_sibling:
                print("If sibling exists")
                name = check_element_and_children(prev_sibling)
                if name:
                    return name
            
            current = current.parent
            distance += 1
        
        return None
    
    def get_linkedin_profile(self, company_name: str, person_name: str) -> Optional[str]:
        """Use SERP API to find the LinkedIn profile of the person"""
        query = f"{company_name} {person_name} LinkedIn"

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serp_api_key,
            "num": 1  # Get only the first result
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            organic_results = results.get('organic_results', [])
            if organic_results:
                first_result = organic_results[0]
                link = first_result.get('link', '')
                # Verify that the link is a LinkedIn profile
                if 'linkedin.com/in/' in link or 'linkedin.com/pub/' in link:
                    return link
            return None
        except Exception as e:
            print(f"Error fetching LinkedIn profile for {person_name}: {e}")
            return None

    def remove_duplicates(self, people: List[Dict]) -> List[Dict]:
        """Remove duplicate entries based on name"""
        seen_names = set()
        unique_people = []

        for person in people:
            if person['name'] not in seen_names:
                seen_names.add(person['name'])
                unique_people.append(person)

        return unique_people

    def extract_people_info(self, html: str, company_name: str) -> List[Dict]:
        """Extract names and titles from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        results = []
        
        for keyword in self.title_keywords:
            # Look for elements containing the keyword, excluding style/script
            elements = soup.find_all(
                lambda tag: tag.name not in ['script', 'style'] and tag.string and 
                           re.search(r'\b{}\b'.format(re.escape(keyword)), tag.string, re.IGNORECASE)
            )
            
            for element in elements:
                print("This is element text",element.text)
                # First try to find name in same text
                name = self.find_name_near_title(element)
                
                # If no name found in same text, look in nearby tags
                if not name:
                    print("No name found in near tags, looking in text")
                    name = self.find_name_in_text(element.text, keyword)


                if name:
                    # Get LinkedIn profile using SERP API
                    linkedin_profile = self.get_linkedin_profile(company_name, name)

                    results.append({
                        'name': name,
                        'title': keyword,
                        'company_name': company_name,
                        'context': element.text.strip(),
                        'linkedin': linkedin_profile
                    })
        
        return results

    def remove_duplicates(self, people: List[Dict]) -> List[Dict]:
        """Remove duplicate entries based on name"""
        seen_names = set()
        unique_people = []
        
        for person in people:
            if person['name'] not in seen_names:
                seen_names.add(person['name'])
                unique_people.append(person)
        
        return unique_people
    
    def calculate_string_similarity(str1, str2):
        """Calculate similarity between two strings using SequenceMatcher"""
        if pd.isna(str1) or pd.isna(str2):
            return 0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    @staticmethod
    def normalize_linkedin_url(url: str) -> str:
        """Normalize LinkedIn URL for comparison"""
        if not url:
            return ''
        # Remove protocol (http/https)
        url = re.sub(r'^https?://', '', url)
        # Remove www.
        url = url.replace('www.', '')
        # Remove trailing slash
        url = url.rstrip('/')
        return url.lower()
    

    def evaluate_accuracy(self, scraped_data: List[Dict], ground_truth_data: pd.DataFrame):
        """Compare scraped LinkedIn URLs against ground truth and show matching entries"""
        print("\nComparing LinkedIn URLs...")
        print("="*80)
        
        # Group ground truth data by company name
        company_groups = ground_truth_data.groupby('Company')
        matched_urls = set()
        current_company = None
        company_matches = 0
        
        # Group scraped data by company
        company_scraped_data = {}
        for entry in scraped_data:
            company = entry.get('company_name', '')
            if company not in company_scraped_data:
                company_scraped_data[company] = []
            company_scraped_data[company].append(entry)
        
        # Process each company's data together
        for company_name, company_entries in company_scraped_data.items():
            if company_name in company_groups.groups:
                company_data = company_groups.get_group(company_name)
                total_company_rows = len(company_data)
                company_matches = 0
                
                # Process all entries for this company
                for scraped_entry in company_entries:
                    scraped_linkedin = CompanyWebScraper.normalize_linkedin_url(scraped_entry.get('linkedin', ''))
                    if not scraped_linkedin or scraped_linkedin in matched_urls:
                        continue
                    
                    for _, truth_row in company_data.iterrows():
                        truth_linkedin = CompanyWebScraper.normalize_linkedin_url(truth_row['LinkedIn Profile'])
                        
                        if scraped_linkedin == truth_linkedin and scraped_linkedin not in matched_urls:
                            matched_urls.add(scraped_linkedin)
                            company_matches += 1
                            
                            print(f"\nMatch found in company: {company_name}")
                            print("\nScraped Data:")
                            print(f"Name: {scraped_entry['name']}")
                            print(f"Title: {scraped_entry['title']}")
                            print(f"LinkedIn: {scraped_entry['linkedin']}")
                            print(f"Context: {scraped_entry['context'][:100]}...")
                            
                            print("\nGround Truth Data:")
                            print(f"Name: {truth_row['Full Name']}")
                            print(f"Title: {truth_row['Title']}")
                            print(f"LinkedIn: {truth_row['LinkedIn Profile']}")
                            print("-"*80)
                            break
                
                # Print statistics after all matches for this company
                percentage = (company_matches / total_company_rows * 100)
                print(f"\nStatistics for {company_name}:")
                print(f"Matches found: {company_matches}")
                print(f"Total profiles in dataset: {total_company_rows}")
                print(f"Match percentage: {percentage:.2f}%")
                print("="*80)

    

def get_filtered_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    """Filter dataset to only include rows with specific executive titles"""
    # Define executive title keywords
    title_keywords = [
        'CEO', 'CTO', 'Founder', 'Co-Founder', 
        'Chief Technology Officer', 'Chief Executive Officer', 
        'Co-Founders'
    ]
    
    # Create regex pattern for exact word matches
    pattern = '|'.join(r'\b{}\b'.format(re.escape(title)) for title in title_keywords)
    
    # Filter dataset where Title column matches pattern
    filtered = dataset[dataset['Title'].str.contains(pattern, case=False, regex=True, na=False)]
    print(f"\nFiltered dataset to {len(filtered)} rows matching titles: {', '.join(title_keywords)}")
    
    return filtered

def main():
    serp_api_key = ""
    
    # Ask user whether to run single company or bulk testing
    mode = input("Enter '1' for single company test or '2' for bulk testing from dataset.csv: ")
    
    if mode == '1':
        # Single company flow
        company_url = input("Enter company website URL (e.g., https://company.com): ")
        company_name = input("Enter the company name: ")
        
        scraper = CompanyWebScraper(serp_api_key)
        results = scraper.get_website_content(company_url, company_name)
        
        if results:
            print(f"\nFound the following people at {company_name}:")
            print("="*80)
            for person in results:
                print(f"\nName: {person.get('name')}")
                print(f"Title: {person.get('title')}")
                print(f"LinkedIn: {person.get('linkedin') or 'Not found'}")
                print(f"Context: {person.get('context')[:100]}...")  # Show first 100 chars of context
                print("-"*80)
        else:
            print("\nNo executive information found.")
            
    elif mode == '2':
        # Bulk testing flow
        print("Loading dataset.csv...")
        ground_truth = pd.read_csv('dataset.csv')
        scraped_results = []
        scraper = CompanyWebScraper(serp_api_key)
        filtered_dataset = get_filtered_dataset(ground_truth)

        # Ask user how many companies to process
        num_companies = int(input("Enter the number of companies to process (max 10): "))
        num_companies = min(num_companies, 50)  # Limit to 10 companies
        
        for _, row in filtered_dataset.head(num_companies).iterrows():
            company_name = row['Company']
            domain = row['Domain']
            
            print(f"\nProcessing {company_name}...")
            try:
                results = scraper.get_website_content(domain, company_name)
                if results:
                    scraped_results.extend(results)
            except Exception as e:
                print(f"Error processing {company_name}: {str(e)}")
                continue
        
        # Compare results with ground truth
        if scraped_results:
            matches = scraper.evaluate_accuracy(scraped_results, filtered_dataset)
            
            if not matches:
                print("\nNo matching LinkedIn profiles found in any of the processed companies.")
                print("\nAll scraped profiles (unmatched):")
                for person in scraped_results:
                    print(f"\nCompany: {person.get('company_name')}")
                    print(f"Name: {person.get('name')}")
                    print(f"Title: {person.get('title')}")
                    print(f"LinkedIn: {person.get('linkedin') or 'Not found'}")
        else:
            print("\nNo executive information found for any company.")
    
    else:
        print("Invalid mode selected. Please run again and select '1' or '2'.")

if __name__ == "__main__":
    main()