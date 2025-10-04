"""
Blog Data Fetching Module for Resume Evaluation

This module fetches and processes blog content from various platforms:
- Medium
- Dev.to  
- Personal blogs (RSS/Atom feeds)
- GitHub Pages

Supports comprehensive blog analysis for technical communication assessment.
"""

import requests
import json
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML content."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta'}
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
    
    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)
    
    def get_text(self):
        return ' '.join(self.text_parts)


def strip_html_tags(html_content: str) -> str:
    """Strip HTML tags and return plain text."""
    if not html_content:
        return ''
    
    extractor = HTMLTextExtractor()
    try:
        extractor.feed(html_content)
        return extractor.get_text()
    except:
        # Fallback to simple regex if parsing fails
        clean = re.sub('<.*?>', ' ', html_content)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()


logger = logging.getLogger(__name__)

class BlogDataFetcher:
    """Fetches and processes blog content from multiple platforms."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ResumeEvaluator/1.0)'
        })
        
        # Platform-specific extractors
        self.extractors = {
            'medium.com': self._extract_medium_data,
            'dev.to': self._extract_devto_data,
            'hashnode': self._extract_hashnode_data,
            'substack': self._extract_substack_data,
            'github.io': self._extract_github_pages_data,
            'ghost': self._extract_generic_blog_data,
            'wordpress': self._extract_wordpress_data,
            'blogger': self._extract_generic_blog_data,
            'tumblr': self._extract_generic_blog_data,
            'wix': self._extract_generic_blog_data,
            'default': self._extract_generic_blog_data
        }
    
    def fetch_blog_data(self, blog_urls: List[str]) -> Dict:
        """
        Fetch comprehensive blog data from multiple URLs.
        
        Args:
            blog_urls: List of blog URLs or profile URLs
            
        Returns:
            Dictionary containing blog analysis data
        """
        if not blog_urls:
            return self._empty_blog_data()
            
        all_posts = []
        platforms = set()
        total_engagement = 0
        
        for url in blog_urls:
            try:
                platform = self._detect_platform(url)
                platforms.add(platform)
                
                extractor = self.extractors.get(platform, self.extractors['default'])
                posts = extractor(url)
                
                all_posts.extend(posts)
                logger.info(f"Fetched {len(posts)} posts from {platform}: {url}")
                
            except Exception as e:
                logger.warning(f"Failed to fetch blog data from {url}: {e}")
                continue
        
        # Analyze collected data
        blog_data = self._analyze_blog_content(all_posts, platforms)
        logger.info(f"Blog analysis complete: {len(all_posts)} total posts across {len(platforms)} platforms")
        
        return blog_data
    
    def _detect_platform(self, url: str) -> str:
        """Detect blog platform from URL."""
        domain = urlparse(url).netloc.lower()
        
        # Popular blogging platforms
        if 'medium.com' in domain:
            return 'medium.com'
        elif 'dev.to' in domain:
            return 'dev.to'
        elif 'hashnode' in domain:
            return 'hashnode'
        elif 'substack.com' in domain:
            return 'substack'
        elif 'github.io' in domain:
            return 'github.io'
        elif 'ghost.io' in domain or 'ghost.org' in domain:
            return 'ghost'
        elif 'wordpress.com' in domain or 'wp.com' in domain:
            return 'wordpress'
        elif 'blogger.com' in domain or 'blogspot.com' in domain:
            return 'blogger'
        elif 'tumblr.com' in domain:
            return 'tumblr'
        elif 'wix.com' in domain:
            return 'wix'
        else:
            return 'default'
    
    def _extract_medium_data(self, url: str) -> List[Dict]:
        """Extract blog posts from Medium profile."""
        posts = []
        
        try:
            # Medium profile URL patterns
            if '/users/' in url or '/@' in url:
                # Extract username and get profile data
                username = self._extract_medium_username(url)
                if username:
                    posts = self._fetch_medium_posts(username)
            else:
                # Direct Medium post URL
                post = self._fetch_single_medium_post(url)
                if post:
                    posts = [post]
                    
        except Exception as e:
            logger.error(f"Medium extraction failed for {url}: {e}")
            
        return posts
    
    def _extract_medium_username(self, url: str) -> Optional[str]:
        """Extract Medium username from profile URL."""
        # Handle different Medium URL patterns
        if '/@' in url:
            return url.split('/@')[1].split('/')[0].split('?')[0]
        elif '/users/' in url:
            return url.split('/users/')[1].split('/')[0].split('?')[0]
        return None
    
    def _fetch_medium_posts(self, username: str) -> List[Dict]:
        """Fetch posts for a Medium username."""
        posts = []
        
        try:
            # Try Medium's RSS feed (most reliable method)
            rss_url = f"https://medium.com/feed/@{username}"
            response = self.session.get(rss_url, timeout=10)
            
            if response.status_code == 200:
                posts = self._parse_rss_feed(response.text, 'medium')
                
        except Exception as e:
            logger.warning(f"Medium RSS fetch failed for {username}: {e}")
            
        return posts
    
    def _fetch_single_medium_post(self, url: str) -> Optional[Dict]:
        """Fetch a single Medium post."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Extract title and content from HTML
                html = response.text
                title_match = re.search(r'<title>([^<]+)</title>', html)
                title = title_match.group(1).split('|')[0].strip() if title_match else 'Untitled'
                
                # Try to extract article content
                article_patterns = [
                    r'<article[^>]*>(.*?)</article>',
                    r'<div class=".*?article.*?"[^>]*>(.*?)</div>',
                    r'<main[^>]*>(.*?)</main>'
                ]
                
                content = ''
                for pattern in article_patterns:
                    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                    if match:
                        content = match.group(1)
                        break
                
                clean_content = strip_html_tags(content) if content else ''
                word_count = len(clean_content.split()) if clean_content else 0
                
                return {
                    'title': title,
                    'url': url,
                    'description': clean_content[:500] if clean_content else '',
                    'published_date': None,
                    'platform': 'medium',
                    'word_count': word_count
                }
        except Exception as e:
            logger.warning(f"Failed to fetch Medium post {url}: {e}")
        return None
    
    def _extract_devto_data(self, url: str) -> List[Dict]:
        """Extract blog posts from Dev.to profile."""
        posts = []
        
        try:
            # Dev.to API is available for public posts
            if '/users/' in url or url.endswith('.dev'):
                username = self._extract_devto_username(url)
                if username:
                    api_url = f"https://dev.to/api/articles?username={username}"
                    response = self.session.get(api_url, timeout=10)
                    
                    if response.status_code == 200:
                        articles = response.json()
                        posts = self._process_devto_articles(articles)
                        
        except Exception as e:
            logger.error(f"Dev.to extraction failed for {url}: {e}")
            
        return posts
    
    def _extract_devto_username(self, url: str) -> Optional[str]:
        """Extract Dev.to username from URL."""
        if '/users/' in url:
            return url.split('/users/')[1].split('/')[0]
        elif url.count('/') >= 3:
            return url.split('/')[3]
        return None
    
    def _process_devto_articles(self, articles: List[Dict]) -> List[Dict]:
        """Process Dev.to articles from API response."""
        posts = []
        for article in articles[:10]:  # Limit to 10 most recent
            posts.append({
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'description': article.get('description', '')[:500],
                'published_date': article.get('published_at', ''),
                'platform': 'dev.to',
                'word_count': article.get('reading_time_minutes', 0) * 200  # Estimate
            })
        return posts
    
    def _extract_hashnode_data(self, url: str) -> List[Dict]:
        """Extract blog posts from Hashnode."""
        posts = []
        
        try:
            # Hashnode blogs have RSS feeds at /rss.xml
            feed_urls = [
                urljoin(url, '/rss.xml'),
                urljoin(url, '/feed.xml'),
                urljoin(url, '/atom.xml')
            ]
            
            for feed_url in feed_urls:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code == 200:
                        posts = self._parse_rss_feed(response.text, 'hashnode')
                        if posts:
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Hashnode extraction failed for {url}: {e}")
            
        return posts
    
    def _extract_substack_data(self, url: str) -> List[Dict]:
        """Extract blog posts from Substack."""
        posts = []
        
        try:
            # Substack has RSS feed at /feed
            feed_urls = [
                urljoin(url, '/feed'),
                urljoin(url, '/feed/'),
                urljoin(url, '/rss'),
            ]
            
            for feed_url in feed_urls:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code == 200:
                        posts = self._parse_rss_feed(response.text, 'substack')
                        if posts:
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Substack extraction failed for {url}: {e}")
            
        return posts
    
    def _extract_wordpress_data(self, url: str) -> List[Dict]:
        """Extract blog posts from WordPress sites."""
        posts = []
        
        try:
            # WordPress has multiple feed endpoints
            feed_urls = [
                urljoin(url, '/feed/'),
                urljoin(url, '/feed'),
                urljoin(url, '/?feed=rss2'),
                urljoin(url, '/rss'),
                urljoin(url, '/atom'),
                urljoin(url, '/wp-json/wp/v2/posts')  # WordPress REST API
            ]
            
            for feed_url in feed_urls:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code == 200:
                        # Try REST API first
                        if 'wp-json' in feed_url:
                            try:
                                wp_posts = response.json()
                                posts = self._process_wordpress_api(wp_posts)
                                if posts:
                                    break
                            except:
                                continue
                        else:
                            # Try as RSS feed
                            posts = self._parse_rss_feed(response.text, 'wordpress')
                            if posts:
                                break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"WordPress extraction failed for {url}: {e}")
            
        return posts
    
    def _process_wordpress_api(self, wp_posts: List[Dict]) -> List[Dict]:
        """Process WordPress REST API response."""
        posts = []
        for post in wp_posts[:10]:  # Limit to 10 most recent
            content = post.get('content', {}).get('rendered', '')
            clean_content = strip_html_tags(content) if content else ''
            
            posts.append({
                'title': strip_html_tags(post.get('title', {}).get('rendered', '')),
                'url': post.get('link', ''),
                'description': clean_content[:500],
                'published_date': post.get('date', ''),
                'platform': 'wordpress',
                'word_count': len(clean_content.split()) if clean_content else 0
            })
        return posts
    
    def _extract_github_pages_data(self, url: str) -> List[Dict]:
        """Extract blog posts from GitHub Pages site."""
        posts = []
        
        try:
            # Try common RSS/Atom feed locations
            feed_urls = [
                urljoin(url, '/feed.xml'),
                urljoin(url, '/atom.xml'),
                urljoin(url, '/rss.xml'),
                urljoin(url, '/index.xml')
            ]
            
            for feed_url in feed_urls:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code == 200:
                        posts = self._parse_rss_feed(response.text, 'github_pages')
                        if posts:
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"GitHub Pages extraction failed for {url}: {e}")
            
        return posts
    
    def _extract_generic_blog_data(self, url: str) -> List[Dict]:
        """Extract blog posts from generic blog sites."""
        posts = []
        
        try:
            # First, try common RSS/Atom feed locations
            common_feed_paths = [
                '/feed/', '/feed', '/rss/', '/rss', '/atom/', '/atom',
                '/feed.xml', '/rss.xml', '/atom.xml', '/index.xml',
                '/?feed=rss2', '/?feed=atom', '/blog/feed', '/blog/rss',
                '/posts/feed', '/articles/feed'
            ]
            
            # Try common feed locations first (faster)
            for path in common_feed_paths:
                feed_url = urljoin(url, path)
                try:
                    response = self.session.get(feed_url, timeout=10)
                    if response.status_code == 200 and ('xml' in response.headers.get('content-type', '').lower() or '<?xml' in response.text[:100]):
                        posts = self._parse_rss_feed(response.text, 'generic')
                        if posts:
                            logger.info(f"Found RSS feed at: {feed_url}")
                            return posts
                except:
                    continue
            
            # If no common feeds found, try to discover feeds from HTML
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    feed_urls = self._discover_feeds(response.text, url)
                    
                    for feed_url in feed_urls:
                        try:
                            feed_response = self.session.get(feed_url, timeout=10)
                            if feed_response.status_code == 200:
                                posts = self._parse_rss_feed(feed_response.text, 'generic')
                                if posts:
                                    logger.info(f"Found RSS feed via discovery: {feed_url}")
                                    break
                        except:
                            continue
                    
                    # Last resort: try to extract blog posts from HTML
                    if not posts:
                        posts = self._extract_from_html(response.text, url)
                        if posts:
                            logger.info(f"Extracted posts from HTML: {url}")
            except:
                pass
                        
        except Exception as e:
            logger.error(f"Generic blog extraction failed for {url}: {e}")
            
        return posts
    
    def _parse_rss_feed(self, feed_content: str, platform: str) -> List[Dict]:
        """Parse RSS/Atom feed content."""
        posts = []
        
        try:
            root = ET.fromstring(feed_content)
            
            # Handle both RSS and Atom formats
            if root.tag == 'rss':
                items = root.findall('.//item')
            else:  # Atom
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for item in items[:10]:  # Limit to 10 most recent posts
                post = self._parse_feed_item(item, platform)
                if post:
                    posts.append(post)
                    
        except Exception as e:
            logger.error(f"RSS parsing failed: {e}")
            
        return posts
    
    def _parse_feed_item(self, item, platform: str) -> Optional[Dict]:
        """Parse individual RSS/Atom item."""
        try:
            # Extract common fields
            title = self._get_text_content(item, ['title'])
            link = self._get_text_content(item, ['link', 'guid'])
            
            # Try to get full content from multiple sources
            content = self._get_text_content(item, [
                '{http://purl.org/rss/1.0/modules/content/}encoded',
                'content',
                'description',
                'summary'
            ])
            
            pub_date = self._get_text_content(item, ['pubDate', 'published'])
            
            if title and link:
                # Clean HTML from content and calculate word count
                clean_content = strip_html_tags(content) if content else ''
                word_count = len(clean_content.split()) if clean_content else 0
                
                return {
                    'title': title,
                    'url': link,
                    'description': clean_content[:500] if clean_content else '',
                    'published_date': pub_date,
                    'platform': platform,
                    'word_count': word_count
                }
                
        except Exception as e:
            logger.warning(f"Failed to parse feed item: {e}")
            
        return None
    
    def _get_text_content(self, element, tag_names: List[str]) -> Optional[str]:
        """Get text content from XML element by tag names."""
        for tag in tag_names:
            # Try direct find first
            elem = element.find(tag)
            if elem is None:
                # Try with namespace-aware search
                elem = element.find(f'.//{tag}')
            
            if elem is not None:
                # Get text content (including all child text)
                text = ''.join(elem.itertext()) if hasattr(elem, 'itertext') else elem.text
                if text:
                    return text
                # Fallback to href attribute for link tags
                if elem.get('href'):
                    return elem.get('href')
        return None
    
    def _discover_feeds(self, html_content: str, base_url: str) -> List[str]:
        """Discover RSS/Atom feeds from HTML content."""
        feeds = []
        
        # Look for feed links in HTML
        feed_patterns = [
            r'<link[^>]*type=["\']application/rss\+xml["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*type=["\']application/atom\+xml["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*type=["\']application/rss\+xml["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*type=["\']application/atom\+xml["\']',
            r'<link[^>]*href=["\']([^"\']*feed[^"\']*)["\']',
            r'<link[^>]*href=["\']([^"\']*rss[^"\']*)["\']',
            r'<a[^>]*href=["\']([^"\']*feed[^"\']*)["\']',
            r'<a[^>]*href=["\']([^"\']*rss[^"\']*)["\']'
        ]
        
        for pattern in feed_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                feed_url = urljoin(base_url, match)
                if feed_url not in feeds and feed_url != base_url:
                    feeds.append(feed_url)
        
        return feeds
    
    def _extract_from_html(self, html_content: str, base_url: str) -> List[Dict]:
        """
        Fallback method to extract blog posts directly from HTML.
        This is used when no RSS feed is available.
        """
        posts = []
        
        try:
            # Look for common blog post patterns in HTML
            # This is a best-effort approach for blogs without feeds
            
            # Pattern 1: Look for article tags
            article_pattern = r'<article[^>]*>(.*?)</article>'
            articles = re.findall(article_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for article in articles[:5]:  # Limit to first 5
                # Try to extract title
                title_match = re.search(r'<h[12][^>]*>(.*?)</h[12]>', article, re.IGNORECASE)
                title = strip_html_tags(title_match.group(1)) if title_match else 'Untitled Post'
                
                # Try to extract link
                link_match = re.search(r'<a[^>]*href=["\']([^"\']+)["\']', article)
                link = urljoin(base_url, link_match.group(1)) if link_match else base_url
                
                # Extract content
                clean_content = strip_html_tags(article)
                word_count = len(clean_content.split()) if clean_content else 0
                
                if title and word_count > 50:  # Only add if substantial content
                    posts.append({
                        'title': title[:200],
                        'url': link,
                        'description': clean_content[:500],
                        'published_date': None,
                        'platform': 'generic',
                        'word_count': word_count
                    })
            
            # If no articles found, try looking for common blog post class patterns
            if not posts:
                post_patterns = [
                    r'<div[^>]*class=["\'][^"\']*post[^"\']*["\'][^>]*>(.*?)</div>',
                    r'<div[^>]*class=["\'][^"\']*blog[^"\']*["\'][^>]*>(.*?)</div>',
                    r'<div[^>]*class=["\'][^"\']*entry[^"\']*["\'][^>]*>(.*?)</div>'
                ]
                
                for pattern in post_patterns:
                    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                    if matches:
                        for match in matches[:5]:
                            title_match = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', match, re.IGNORECASE)
                            title = strip_html_tags(title_match.group(1)) if title_match else 'Untitled Post'
                            
                            clean_content = strip_html_tags(match)
                            word_count = len(clean_content.split()) if clean_content else 0
                            
                            if word_count > 50:
                                posts.append({
                                    'title': title[:200],
                                    'url': base_url,
                                    'description': clean_content[:500],
                                    'published_date': None,
                                    'platform': 'generic',
                                    'word_count': word_count
                                })
                        if posts:
                            break
                            
        except Exception as e:
            logger.warning(f"HTML extraction failed: {e}")
        
        return posts
    
    def _analyze_blog_content(self, posts: List[Dict], platforms: set) -> Dict:
        """Analyze collected blog posts and generate evaluation data."""
        if not posts:
            return self._empty_blog_data()
        
        # Calculate metrics
        total_posts = len(posts)
        total_words = sum(post.get('word_count', 0) for post in posts)
        avg_words_per_post = total_words / total_posts if total_posts > 0 else 0
        
        # Analyze technical content
        technical_score = self._calculate_technical_score(posts)
        consistency_score = self._calculate_consistency_score(posts)
        quality_score = self._calculate_quality_score(posts)
        
        # Overall blog score (0-10)
        blog_score = min(10.0, (technical_score + consistency_score + quality_score) / 3)
        
        return {
            'total_blogs': total_posts,
            'blog_score': round(blog_score, 1),
            'blog_details': f"Found {total_posts} posts across {len(platforms)} platforms. "
                          f"Average {int(avg_words_per_post)} words/post. "
                          f"Technical depth: {technical_score:.1f}/10",
            'blogs': posts[:5],  # Top 5 posts for evaluation
            'platforms': list(platforms),
            'metrics': {
                'total_words': total_words,
                'avg_words_per_post': int(avg_words_per_post),
                'technical_score': technical_score,
                'consistency_score': consistency_score,
                'quality_score': quality_score
            }
        }
    
    def _calculate_technical_score(self, posts: List[Dict]) -> float:
        """Calculate technical content score based on keywords and topics."""
        technical_keywords = [
            'algorithm', 'architecture', 'api', 'database', 'framework',
            'cloud', 'docker', 'kubernetes', 'microservices', 'devops',
            'ci/cd', 'cicd', 'pipeline', 'testing', 'performance', 'security', 'scalability',
            'python', 'javascript', 'react', 'node', 'django', 'flask', 'typescript',
            'aws', 'azure', 'gcp', 'machine learning', 'ai', 'data science',
            'backend', 'frontend', 'fullstack', 'deployment', 'infrastructure',
            'git', 'github', 'automation', 'monitoring', 'logging',
            'rest', 'graphql', 'websocket', 'sql', 'nosql', 'redis',
            'nginx', 'apache', 'server', 'networking', 'authentication',
            'hackathon', 'coding', 'programming', 'software', 'development',
            'debugging', 'optimization', 'refactor', 'design pattern'
        ]
        
        total_score = 0
        for post in posts:
            content = (post.get('title', '') + ' ' + post.get('description', '')).lower()
            keyword_count = sum(1 for keyword in technical_keywords if keyword in content)
            # Better scoring: 1 point per keyword, up to 10 points per post
            post_score = min(10, keyword_count * 1.0)
            total_score += post_score
        
        return total_score / len(posts) if posts else 0
    
    def _calculate_consistency_score(self, posts: List[Dict]) -> float:
        """Calculate consistency score based on posting frequency and quality."""
        if len(posts) < 2:
            return 5.0  # Neutral score for single post
        
        # Score based on number of posts
        post_count_score = min(10, len(posts) * 1.5)
        
        # Bonus for regular posting (this would need date analysis)
        regularity_score = 7.0  # Default good score
        
        return (post_count_score + regularity_score) / 2
    
    def _calculate_quality_score(self, posts: List[Dict]) -> float:
        """Calculate quality score based on post length and depth."""
        if not posts:
            return 0
        
        avg_word_count = sum(post.get('word_count', 0) for post in posts) / len(posts)
        
        # Score based on average post length
        if avg_word_count >= 1000:
            return 10.0  # Excellent detailed posts
        elif avg_word_count >= 500:
            return 8.0   # Good depth
        elif avg_word_count >= 200:
            return 6.0   # Decent length
        else:
            return 4.0   # Short posts
    
    def _empty_blog_data(self) -> Dict:
        """Return empty blog data structure."""
        return {
            'total_blogs': 0,
            'blog_score': 0,
            'blog_details': 'No blog content found',
            'blogs': [],
            'platforms': [],
            'metrics': {
                'total_words': 0,
                'avg_words_per_post': 0,
                'technical_score': 0,
                'consistency_score': 0,
                'quality_score': 0
            }
        }


def extract_blog_urls_from_profiles(profiles: List) -> List[str]:
    """
    Extract blog URLs from resume profile data.
    
    Args:
        profiles: List of profile objects or dictionaries from resume basics
        
    Returns:
        List of blog URLs
    """
    blog_urls = []
    blog_indicators = [
        'medium', 'dev.to', 'blog', 'write', 'hashnode', 'substack',
        'ghost', 'wordpress', 'blogger', 'blogspot', 'tumblr',
        'wix', 'squarespace', 'notion', 'telegraph', 'write.as',
        'bearblog', 'blot.im', 'micro.blog', 'svbtle', 'posthaven'
    ]
    
    for profile in profiles:
        if not profile:
            continue
        
        # Handle both Pydantic models and dictionaries
        if isinstance(profile, dict):
            url = profile.get('url', '')
            network = profile.get('network', '').lower()
        else:
            # Pydantic model
            url = getattr(profile, 'url', '')
            network = getattr(profile, 'network', '').lower() if hasattr(profile, 'network') else ''
        
        if url and any(indicator in url.lower() or indicator in network for indicator in blog_indicators):
            blog_urls.append(url)
    
    return blog_urls


def fetch_and_analyze_blog_data(profiles: List) -> Optional[Dict]:
    """
    Main function to fetch and analyze blog data from resume profiles.
    
    Args:
        profiles: List of profile objects or dictionaries from resume
        
    Returns:
        Blog analysis data or None if no blogs found
    """
    try:
        blog_urls = extract_blog_urls_from_profiles(profiles)
        
        if not blog_urls:
            logger.info("No blog URLs found in resume profiles")
            return None
        
        logger.info(f"Found {len(blog_urls)} blog URL(s): {blog_urls}")
        
        fetcher = BlogDataFetcher()
        blog_data = fetcher.fetch_blog_data(blog_urls)
        
        if blog_data and blog_data.get('total_blogs', 0) > 0:
            logger.info(f"Successfully analyzed {blog_data['total_blogs']} blog posts")
            return blog_data
        else:
            logger.info("No blog posts could be fetched from provided URLs")
            return None
            
    except Exception as e:
        logger.error(f"Blog data fetching failed: {e}", exc_info=True)
        return None