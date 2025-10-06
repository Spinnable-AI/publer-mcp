"""
Blog content parsing utilities for Publer MCP.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import httpx
import asyncio
from bs4 import BeautifulSoup


class BlogContentParser:
    """
    Parser for extracting metadata and content from blog posts.
    
    Extracts title, description, preview images, keywords, and other metadata
    useful for creating optimized social media posts.
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize blog content parser.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.user_agent = "Mozilla/5.0 (compatible; Publer-MCP/1.0; Social Media Bot)"
    
    async def parse_blog_url(self, blog_url: str) -> Dict[str, Any]:
        """
        Parse blog URL and extract metadata for social media optimization.
        
        Args:
            blog_url: URL of the blog post to parse
            
        Returns:
            Dict containing extracted metadata and content analysis
        """
        try:
            # Validate URL
            if not self._is_valid_url(blog_url):
                return {
                    "error": "Invalid URL format",
                    "url": blog_url
                }
            
            # Fetch blog content
            content_data = await self._fetch_url_content(blog_url)
            if content_data.get("error"):
                return content_data
            
            html_content = content_data["html"]
            final_url = content_data["final_url"]
            
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract metadata
            metadata = {
                "url": final_url,
                "title": self._extract_title(soup),
                "description": self._extract_description(soup),
                "preview_image": self._extract_preview_image(soup, final_url),
                "keywords": self._extract_keywords(soup),
                "author": self._extract_author(soup),
                "published_date": self._extract_published_date(soup),
                "reading_time": self._estimate_reading_time(soup),
                "word_count": self._count_words(soup),
                "content_snippet": self._extract_content_snippet(soup),
                "social_tags": self._extract_social_tags(soup)
            }
            
            # Clean up and validate metadata
            return self._clean_metadata(metadata)
            
        except Exception as e:
            return {
                "error": f"Failed to parse blog content: {str(e)}",
                "url": blog_url
            }
    
    async def _fetch_url_content(self, url: str) -> Dict[str, Any]:
        """Fetch HTML content from URL with proper error handling."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                headers = {"User-Agent": self.user_agent}
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return {
                        "error": f"HTTP {response.status_code}: Failed to fetch content",
                        "url": url
                    }
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    return {
                        "error": f"Non-HTML content type: {content_type}",
                        "url": url
                    }
                
                return {
                    "html": response.text,
                    "final_url": str(response.url)
                }
                
        except httpx.TimeoutException:
            return {
                "error": f"Request timeout after {self.timeout} seconds",
                "url": url
            }
        except httpx.RequestError as e:
            return {
                "error": f"Network error: {str(e)}",
                "url": url
            }
        except Exception as e:
            return {
                "error": f"Unexpected error fetching content: {str(e)}",
                "url": url
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title with fallback options."""
        # Try Open Graph title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try Twitter title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # Try HTML title tag
        title_tag = soup.find('title')
        if title_tag and title_tag.text:
            return title_tag.text.strip()
        
        # Try h1 tag
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.text:
            return h1_tag.text.strip()
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page description with fallback options."""
        # Try Open Graph description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Try Twitter description  
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            return twitter_desc['content'].strip()
        
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Extract from first paragraph
        first_p = soup.find('p')
        if first_p and first_p.text:
            return first_p.text.strip()[:200]
        
        return None
    
    def _extract_preview_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract preview image with fallback options."""
        # Try Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return self._resolve_url(og_image['content'], base_url)
        
        # Try Twitter image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return self._resolve_url(twitter_image['content'], base_url)
        
        # Try to find first content image
        content_area = soup.find(['article', 'main', 'div'], class_=re.compile(r'content|post|article', re.I))
        if content_area:
            img = content_area.find('img')
            if img and img.get('src'):
                return self._resolve_url(img['src'], base_url)
        
        # Try any image in the page
        img = soup.find('img')
        if img and img.get('src'):
            src = img['src']
            if not src.endswith(('.svg', '.gif')) and 'logo' not in src.lower():
                return self._resolve_url(src, base_url)
        
        return None
    
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from meta tags and content."""
        keywords = []
        
        # Try meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords.extend([kw.strip() for kw in meta_keywords['content'].split(',')])
        
        # Extract from headings
        headings = soup.find_all(['h1', 'h2', 'h3'])
        for heading in headings[:5]:  # Limit to first 5 headings
            text = heading.get_text().strip()
            if text and len(text.split()) <= 4:  # Short headings are likely keywords
                keywords.append(text)
        
        # Extract hashtags if present
        text_content = soup.get_text()
        hashtags = re.findall(r'#(\w+)', text_content)
        keywords.extend(hashtags[:5])  # Limit hashtags
        
        # Clean and deduplicate
        cleaned_keywords = []
        for kw in keywords:
            kw = kw.strip().lower()
            if kw and len(kw) > 2 and kw not in cleaned_keywords:
                cleaned_keywords.append(kw)
        
        return cleaned_keywords[:10]  # Limit to 10 keywords
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information."""
        # Try JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    author = data.get('author')
                    if isinstance(author, dict):
                        return author.get('name')
                    elif isinstance(author, str):
                        return author
            except:
                pass
        
        # Try meta author
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content'].strip()
        
        # Try byline patterns
        byline = soup.find(['span', 'div', 'p'], class_=re.compile(r'author|byline|writer', re.I))
        if byline and byline.text:
            return byline.text.strip()
        
        return None
    
    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract published date."""
        # Try JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    date_published = data.get('datePublished')
                    if date_published:
                        return date_published
            except:
                pass
        
        # Try meta tags
        meta_date = soup.find('meta', property='article:published_time')
        if meta_date and meta_date.get('content'):
            return meta_date['content']
        
        # Try time tag
        time_tag = soup.find('time')
        if time_tag:
            datetime_attr = time_tag.get('datetime')
            if datetime_attr:
                return datetime_attr
            elif time_tag.text:
                return time_tag.text.strip()
        
        return None
    
    def _estimate_reading_time(self, soup: BeautifulSoup) -> Optional[int]:
        """Estimate reading time in minutes."""
        word_count = self._count_words(soup)
        if word_count:
            # Assume 200 words per minute average reading speed
            return max(1, round(word_count / 200))
        return None
    
    def _count_words(self, soup: BeautifulSoup) -> Optional[int]:
        """Count words in the main content."""
        # Try to find main content area
        content_selectors = [
            'article', 'main', '[role="main"]',
            '.post-content', '.entry-content', '.content',
            '.post-body', '.article-content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
        
        # Fallback to body if no content area found
        if not content_area:
            content_area = soup.find('body')
        
        if content_area:
            # Remove script and style elements
            for elem in content_area(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            
            text = content_area.get_text()
            words = text.split()
            return len(words)
        
        return None
    
    def _extract_content_snippet(self, soup: BeautifulSoup, max_length: int = 300) -> Optional[str]:
        """Extract a snippet of the main content."""
        # Similar to word count, find main content
        content_selectors = [
            'article', 'main', '[role="main"]',
            '.post-content', '.entry-content', '.content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
        
        if not content_area:
            content_area = soup.find('body')
        
        if content_area:
            # Remove unwanted elements
            for elem in content_area(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()
            
            # Get first paragraph or text
            first_p = content_area.find('p')
            if first_p and first_p.text:
                text = first_p.text.strip()
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text
        
        return None
    
    def _extract_social_tags(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract social media specific meta tags."""
        return {
            "twitter_card": self._get_meta_content(soup, 'name', 'twitter:card'),
            "twitter_site": self._get_meta_content(soup, 'name', 'twitter:site'),
            "og_type": self._get_meta_content(soup, 'property', 'og:type'),
            "og_site_name": self._get_meta_content(soup, 'property', 'og:site_name')
        }
    
    def _get_meta_content(self, soup: BeautifulSoup, attr: str, value: str) -> Optional[str]:
        """Helper to get meta tag content."""
        meta = soup.find('meta', {attr: value})
        return meta.get('content') if meta else None
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs."""
        if url.startswith(('http://', 'https://')):
            return url
        return urljoin(base_url, url)
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except:
            return False
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate extracted metadata."""
        # Remove empty values
        cleaned = {}
        for key, value in metadata.items():
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                    if value:
                        cleaned[key] = value
                elif isinstance(value, (list, dict)):
                    if value:
                        cleaned[key] = value
                else:
                    cleaned[key] = value
        
        # Ensure title exists
        if 'title' not in cleaned and 'url' in cleaned:
            cleaned['title'] = f"Content from {urlparse(cleaned['url']).netloc}"
        
        return cleaned