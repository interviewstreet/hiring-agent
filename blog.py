import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List
from pathlib import Path

def extract_username(url: str, platform: str) -> Optional[str]:
    url = url.strip().rstrip('/')
    if platform == "dev.to":
        match = re.search(r'dev\.to/([^/]+)', url)
        return match.group(1) if match else None
    elif platform == "medium":
        match = re.search(r'medium\.com/@([^/]+)', url)
        if match: return match.group(1)
        match = re.search(r'([^/]+)\.medium\.com', url)
        if match and match.group(1) != "www": return match.group(1)
        return None
    elif platform == "hashnode":
        match = re.search(r'hashnode\.com/@([^/]+)', url)
        if match: return match.group(1)
        match = re.search(r'([^/]+)\.hashnode\.dev', url)
        if match: return match.group(1)
        return None
    return None

def fetch_devto_blogs(username: str) -> List[Dict]:
    try:
        response = requests.get(f"https://dev.to/api/articles?username={username}", timeout=10)
        if response.status_code == 200:
            articles = response.json()
            blogs = []
            for art in articles[:5]:
                blogs.append({
                    "url": art.get("url"),
                    "score": "N/A",
                    "details": f"Title: {art.get('title', '')}\nDescription: {art.get('description', '')}"
                })
            return blogs
    except Exception as e:
        print(f"Error fetching dev.to blogs: {e}")
    return []

def fetch_rss_blogs(feed_url: str) -> List[Dict]:
    try:
        response = requests.get(feed_url, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            blogs = []
            for item in root.findall('./channel/item')[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                categories = [c.text for c in item.findall('category')]
                cat_text = f"Tags: {', '.join(categories)}" if categories else ""
                
                blogs.append({
                    "url": link,
                    "score": "N/A",
                    "details": f"Title: {title}\n{cat_text}"
                })
            return blogs
    except Exception as e:
        print(f"Error fetching RSS blogs from {feed_url}: {e}")
    return []

def identify_platform(url: str) -> Optional[str]:
    url = url.lower()
    if "dev.to" in url: return "dev.to"
    if "medium.com" in url: return "medium"
    if "hashnode.com" in url or "hashnode.dev" in url: return "hashnode"
    return None

def fetch_and_display_blog_info(url: str) -> Dict:
    platform = identify_platform(url)
    if not platform:
        print(f"Unrecognized blog platform for URL: {url}")
        return {}

    username = extract_username(url, platform)
    if not username:
        print(f"Could not extract username from {platform} URL: {url}")
        return {}

    print(f"🔍 Fetching blog articles from {platform} for user {username}...")
    
    blogs = []
    if platform == "dev.to":
        blogs = fetch_devto_blogs(username)
    elif platform == "medium":
        # Medium feed is usually medium.com/feed/@username
        blogs = fetch_rss_blogs(f"https://medium.com/feed/@{username}")
    elif platform == "hashnode":
        # Hashnode feed
        if "hashnode.dev" in url:
            blogs = fetch_rss_blogs(f"https://{username}.hashnode.dev/rss.xml")
        else:
            blogs = fetch_rss_blogs(f"https://hashnode.com/@{username}/rss")

    if not blogs:
        print(f"❌ No articles found on {platform} for {username}")
        return {}

    print(f"✅ Found {len(blogs)} recent articles on {platform}")

    result = {
        "total_blogs": len(blogs),
        "blog_score": "N/A",
        "blog_details": f"Fetched {len(blogs)} articles from {platform}",
        "blogs": blogs
    }

    return result
