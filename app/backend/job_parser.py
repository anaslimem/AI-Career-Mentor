import requests
from bs4 import BeautifulSoup
import re
from tavily import TavilyClient
import os 
import time
import random
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=api_key)  

def search_jobs(job_title: str, n: int = 5):
    """Search for job-related content using Tavily API"""
    try:
        # Fixed typo: reponse -> response
        response = tavily_client.search(
            query=f"{job_title} job requirements skills responsibilities", 
            limit=n,
            search_depth="advanced",
            include_domains=["indeed.com", "linkedin.com", "glassdoor.com", "monster.com", "ziprecruiter.com"]
        )
        return response['results'] if 'results' in response else []
    except Exception as e:
        print(f"Error searching jobs with Tavily: {e}")
        return []

def get_headers():
    """Return randomized headers to avoid bot detection"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }

def is_blocked_domain(url: str) -> bool:
    """Check if domain is known to block scrapers"""
    blocked_domains = [
        'bls.gov', 
        'indeed.com',
        'glassdoor.com', 
        'linkedin.com'
    ]
    domain = urlparse(url).netloc.lower()
    return any(blocked in domain for blocked in blocked_domains)

def fetch_and_clean(url: str, max_retries: int = 3) -> str:
    """
    Fetch and clean content from URL with improved error handling
    """
    if not url or not url.strip():
        print("Empty URL provided")
        return ""
    
    # Check if domain is known to block scrapers
    if is_blocked_domain(url):
        print(f"Skipping known blocked domain: {urlparse(url).netloc}")
        return ""
    
    for attempt in range(max_retries):
        try:
            # Add delay between requests to avoid rate limiting
            if attempt > 0:
                delay = random.uniform(2, 5) * (attempt + 1)
                print(f"Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            
            # Create session for better connection handling
            session = requests.Session()
            session.headers.update(get_headers())
            
            # Send request with timeout and verify SSL
            response = session.get(
                url, 
                timeout=(10, 30),  # (connection timeout, read timeout)
                allow_redirects=True,
                verify=True
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
                tag.extract()
            
            # Extract text content
            text = soup.get_text("\n")
            
            # Clean up text
            text = re.sub(r"\n{3,}", "\n\n", text)  # Replace 3+ newlines with 2
            text = re.sub(r"[ \t]{2,}", " ", text)   # Replace multiple spaces/tabs with single space
            text = text.strip()
            
            if len(text) < 100:  # Too short, probably not useful content
                print(f"Content too short ({len(text)} chars) for URL: {url}")
                return ""
            
            print(f"Successfully fetched {len(text)} characters from {url}")
            return text
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"Access forbidden (403) for {url} - domain may block scrapers")
                return ""
            elif e.response.status_code == 404:
                print(f"Page not found (404) for {url}")
                return ""
            else:
                print(f"HTTP error {e.response.status_code} for {url}: {e}")
        
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error for {url}: {e}")
            if attempt == max_retries - 1:
                return ""
        
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for {url}: {e}")
            if attempt == max_retries - 1:
                return ""
        
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            if attempt == max_retries - 1:
                return ""
        
        except Exception as e:
            print(f"Unexpected error processing {url}: {e}")
            return ""
    
    print(f"Failed to fetch {url} after {max_retries} attempts")
    return ""


