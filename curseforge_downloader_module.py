#!/usr/bin/env python3
"""
CurseForge Mod Downloader Module
Modified for use as a module with the Flask web application
"""

import os
import sys
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import io

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# CurseForge API endpoints
CURSEFORGE_API_BASE = "https://api.curseforge.com/v1"
CURSEFORGE_API_KEY = "$2a$10$pyTVCS3SHQdYyzoEa7aSp.OFxee8nl9Kh7zrUYVSzjAcESosq7tqC"  # Provided API key


def parse_html_content(html_content):
    """Parse HTML content and extract CurseForge mod links."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Check for both www and non-www curseforge.com
            if 'curseforge.com/minecraft/mc-mods' in href:
                links.append(href)
        
        return links
    except Exception as e:
        print(f"Error parsing HTML content: {e}")
        return []


def parse_html_file(html_path):
    """Parse the HTML file and extract CurseForge mod links."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return parse_html_content(html_content)
    except Exception as e:
        print(f"Error parsing HTML file: {e}")
        return []


def parse_manifest_json(manifest_content):
    """Parse manifest.json content and extract mod information."""
    try:
        import json
        manifest = json.loads(manifest_content)
        
        mod_info = {
            'minecraft_version': None,
            'modloader': None,
            'mods': []
        }
        
        # Extract Minecraft version
        if 'minecraft' in manifest:
            minecraft_data = manifest['minecraft']
            if 'version' in minecraft_data:
                mod_info['minecraft_version'] = minecraft_data['version']
            
            # Extract modloader information
            if 'modLoaders' in minecraft_data and minecraft_data['modLoaders']:
                mod_info['modloader'] = minecraft_data['modLoaders'][0].get('id', '').replace('forge-', '').replace('fabric-', '').replace('neoforge-', '').replace('quilt-', '')
        
        # Extract mod information
        if 'files' in manifest:
            for file_data in manifest['files']:
                project_id = file_data.get('projectID')
                file_id = file_data.get('fileID')
                required = file_data.get('required', True)
                
                if project_id:
                    mod_info['mods'].append({
                        'project_id': project_id,
                        'file_id': file_id,
                        'required': required
                    })
        
        return mod_info
    except Exception as e:
        print(f"Error parsing manifest.json: {e}")
        return None


def get_mod_ids_from_manifest(manifest_content):
    """Extract mod project IDs from manifest.json content."""
    try:
        mod_info = parse_manifest_json(manifest_content)
        if mod_info:
            return [mod['project_id'] for mod in mod_info['mods']]
        return []
    except Exception as e:
        print(f"Error extracting mod IDs from manifest: {e}")
        return []


def extract_mod_id(mod_url):
    """Extract mod ID from CurseForge URL by making a request and parsing the page."""
    try:
        return get_mod_id_from_slug(mod_url)
    except Exception as e:
        print(f"  Error extracting mod ID: {e}")
        return None


def get_mod_id_from_slug(mod_url):
    """Get mod ID from slug using the API."""
    try:
        slug = mod_url.split('/')[-1]
        print(f"  Searching for slug: {slug}")
        
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        search_url = f"{CURSEFORGE_API_BASE}/mods/search"
        params = {
            "gameId": 432,  # Minecraft game ID
            "slug": slug,
            "pageSize": 1
        }
        
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                mod_id = data['data'][0]['id']
                print(f"  Found mod ID: {mod_id}")
                return mod_id
            else:
                print(f"  No results in API response")
        else:
            print(f"  API request failed: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"  Error searching for mod: {e}")
        return None


def search_mod_by_name(mod_name, content_type='mods'):
    """Search for a mod by name using the API."""
    try:
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        # Map content types to CurseForge class IDs and category filters
        content_config = {
            'mods': {
                'classId': 6,           # Minecraft Mods
                'categoryFilter': None
            },
            'shaders': {
                'classId': 12,         # Texture Packs (shaders are often here)
                'categoryFilter': None
            },
            'datapacks': {
                'classId': 6,          # Data packs are under mods section
                'categoryFilter': None
            },
            'resourcepacks': {
                'classId': 12,         # Texture Packs
                'categoryFilter': None
            }
        }
        
        config = content_config.get(content_type, content_config['mods'])
        
        search_url = f"{CURSEFORGE_API_BASE}/mods/search"
        params = {
            "gameId": 432,  # Minecraft game ID
            "searchFilter": mod_name,
            "pageSize": 25,  # Increase page size to get more results
            "sortField": 1,  # Sort by relevance (1 = Featured, 2 = Popularity)
            "sortOrder": "desc"
        }
        
        # Add class filter for content types that have specific class IDs
        if content_type in ['mods', 'resourcepacks', 'shaders']:
            params["classId"] = config['classId']
        
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                results = data['data']
                
                # Filter results based on content type using categories
                if content_type == 'shaders':
                    # Filter for shader-related categories
                    shader_keywords = ['shader', 'shaders', 'visual', 'graphics', 'lighting', 'iris', 'optifine']
                    filtered_results = [mod for mod in results if 
                                        any(keyword in mod.get('name', '').lower() or 
                                            any(keyword in cat.get('name', '').lower() for cat in mod.get('categories', []))
                                            for keyword in shader_keywords)]
                    if filtered_results:
                        results = filtered_results
                
                elif content_type == 'datapacks':
                    # Filter for data pack related categories
                    datapack_keywords = ['data pack', 'datapack', 'world', 'utility', 'vanilla', 'function']
                    filtered_results = [mod for mod in results if 
                                        any(keyword in mod.get('name', '').lower() or 
                                            any(keyword in cat.get('name', '').lower() for cat in mod.get('categories', []))
                                            for keyword in datapack_keywords)]
                    if filtered_results:
                        results = filtered_results
                
                elif content_type == 'resourcepacks':
                    # Filter for resource pack categories, exclude shaders
                    shader_keywords = ['shader', 'shaders', 'iris', 'optifine']
                    filtered_results = [mod for mod in results if 
                                        not any(keyword in mod.get('name', '').lower() or 
                                               any(keyword in cat.get('name', '').lower() for cat in mod.get('categories', []))
                                               for keyword in shader_keywords)]
                    if filtered_results:
                        results = filtered_results
                
                # Improved exact match prioritization
                # 1. Exact name match (case-insensitive)
                exact_name_matches = [mod for mod in results if mod.get('name', '').lower() == mod_name.lower()]
                # 2. Name contains search term
                name_contains = [mod for mod in results if mod_name.lower() in mod.get('name', '').lower() and mod not in exact_name_matches]
                # 3. Slug contains search term
                slug_contains = [mod for mod in results if mod_name.lower() in mod.get('slug', '').lower() and mod not in exact_name_matches and mod not in name_contains]
                # 4. Remaining results
                other_results = [mod for mod in results if mod not in exact_name_matches and mod not in name_contains and mod not in slug_contains]
                
                # Combine in priority order
                prioritized_results = exact_name_matches + name_contains + slug_contains + other_results
                
                return prioritized_results
        
        return []
    except Exception as e:
        print(f"  Error searching for mod by name: {e}")
        return []


def get_mod_versions(mod_id, game_version=None, mod_loader_type=1):
    """Get available versions for a mod. If game_version is None, returns all versions."""
    try:
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        url = f"{CURSEFORGE_API_BASE}/mods/{mod_id}/files"
        params = {
            "modLoaderType": mod_loader_type
        }
        
        # Only add game_version filter if specified
        if game_version:
            params["gameVersion"] = game_version
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            files = data.get('data', [])
            # Sort by release date (newest first) for better version display
            files.sort(key=lambda x: x.get('fileDate', ''), reverse=True)
            return files
        
        return []
    except Exception as e:
        print(f"  Error getting mod versions: {e}")
        return []


def get_mod_details(mod_id):
    """Get detailed information about a mod."""
    try:
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        url = f"{CURSEFORGE_API_BASE}/mods/{mod_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data')
        
        return None
    except Exception as e:
        print(f"  Error getting mod details: {e}")
        return None


def get_mod_files(mod_id):
    """Get files for a mod from the CurseForge API."""
    try:
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        url = f"{CURSEFORGE_API_BASE}/mods/{mod_id}/files"
        params = {
            "gameVersion": "1.20.1",
            "modLoaderType": 1  # 1 = Forge
        }
        
        print(f"  Getting files for mod {mod_id}...")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            files = data.get('data', [])
            print(f"  Found {len(files)} files")
            return files
        else:
            print(f"  Failed to get files: {response.status_code}")
            return []
        
    except Exception as e:
        print(f"  Error getting mod files: {e}")
        return []


def download_file(file_info, output_dir, max_retries=5):
    """Download a file from CurseForge with enhanced retry logic."""
    download_url = file_info.get('downloadUrl')
    file_name = file_info.get('fileName')
    file_size = file_info.get('fileLength', 0)
    
    if not download_url or not file_name:
        return False, None
    
    print(f"  Downloading: {file_name}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                file_path = output_dir / file_name
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"  Successfully downloaded: {file_name}")
                return True, file_path
            else:
                print(f"  Failed to download: HTTP {response.status_code} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return False, None
                
        except Exception as e:
            print(f"  Error downloading file (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, None
    
    return False, None


def download_mod_by_url(mod_url, output_dir, max_retries=5):
    """Download a single mod from CurseForge using the API."""
    mod_name = mod_url.split('/')[-1]
    print(f"\nProcessing: {mod_name}")
    
    error_details = []
    
    for attempt in range(max_retries):
        try:
            # Get mod ID
            print(f"  Getting mod ID...")
            mod_id = extract_mod_id(mod_url)
            
            if not mod_id:
                error_details.append("Could not find mod ID")
                print(f"  Could not find mod ID")
                return {
                    'success': False,
                    'mod_name': mod_name,
                    'error': "Could not find mod ID",
                    'manual_url': mod_url
                }
            
            # Get mod files
            files = get_mod_files(mod_id)
            
            if not files:
                error_details.append("No files found for 1.20.1 Forge")
                print(f"  No files found for 1.20.1 Forge")
                return {
                    'success': False,
                    'mod_name': mod_name,
                    'error': "No files found for 1.20.1 Forge",
                    'manual_url': mod_url
                }
            
            # Sort by release date (newest first) and get the first release file
            files.sort(key=lambda x: x.get('fileDate', ''), reverse=True)
            
            # Find the best file: try release first, then beta, then alpha
            release_file = None
            for file in files:
                release_type = file.get('releaseType', 1)
                if release_type == 1:
                    release_file = file
                    print(f"  Found release file: {release_file.get('fileName')}")
                    break
            
            if not release_file:
                for file in files:
                    release_type = file.get('releaseType', 1)
                    if release_type == 2:
                        release_file = file
                        print(f"  No release file found, using beta: {release_file.get('fileName')}")
                        break
            
            if not release_file:
                for file in files:
                    release_type = file.get('releaseType', 1)
                    if release_type == 3:
                        release_file = file
                        print(f"  No release/beta file found, using alpha: {release_file.get('fileName')}")
                        break
            
            if not release_file:
                release_file = files[0]
                print(f"  No release/beta/alpha file found, using newest file: {release_file.get('fileName')}")
            
            # Download the file
            success, file_path = download_file(release_file, output_dir, max_retries=5)
            
            if success and file_path:
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                return {
                    'success': True,
                    'mod_name': mod_name,
                    'file_name': release_file.get('fileName'),
                    'file_size_mb': round(file_size_mb, 2),
                    'download_url': mod_url
                }
            else:
                error_details.append("Download failed after retries")
                if attempt < max_retries - 1:
                    print(f"  Retrying...")
                    time.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'mod_name': mod_name,
                        'error': "Download failed after retries",
                        'manual_url': mod_url
                    }
                    
        except Exception as e:
            error_details.append(str(e))
            print(f"  Error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return {
                    'success': False,
                    'mod_name': mod_name,
                    'error': str(e),
                    'manual_url': mod_url
                }
    
    return {
        'success': False,
        'mod_name': mod_name,
        'error': "Unknown error",
        'manual_url': mod_url
    }


def download_mod_by_name(mod_name, output_dir):
    """Search for a mod by name and download the first result."""
    print(f"\nSearching for mod: {mod_name}")
    
    try:
        # Search for the mod
        search_results = search_mod_by_name(mod_name)
        
        if not search_results:
            return {
                'success': False,
                'mod_name': mod_name,
                'error': f"No mods found with name '{mod_name}'",
                'manual_url': None
            }
        
        # Get the first result
        first_result = search_results[0]
        mod_slug = first_result.get('slug')
        mod_id = first_result.get('id')
        
        print(f"  Found mod: {first_result.get('name')} (ID: {mod_id})")
        
        # Construct the mod URL
        mod_url = f"https://www.curseforge.com/minecraft/mc-mods/{mod_slug}"
        
        # Download the mod
        return download_mod_by_url(mod_url, output_dir)
        
    except Exception as e:
        return {
            'success': False,
            'mod_name': mod_name,
            'error': str(e),
            'manual_url': None
        }


def download_specific_version(download_url, file_name, output_dir):
    """Download a specific version of a mod using the direct download URL."""
    print(f"\nDownloading specific version: {file_name}")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(download_url, headers=headers, stream=True, timeout=60)
        
        if response.status_code == 200:
            file_path = output_dir / file_name
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  Successfully downloaded: {file_name}")
            
            return {
                'success': True,
                'file_name': file_name,
                'file_size_mb': round(file_size_mb, 2),
                'download_url': download_url
            }
        else:
            print(f"  Failed to download: HTTP {response.status_code}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}",
                'manual_url': download_url
            }
            
    except Exception as e:
        print(f"  Error downloading file: {e}")
        return {
            'success': False,
            'error': str(e),
            'manual_url': download_url
        }


def process_bulk_download(mod_links, output_dir, job_id=None, progress_callback=None):
    """Process bulk download of mods from a list of URLs."""
    successful_downloads = []
    failed_downloads = []
    error_categories = {}
    total_storage_bytes = 0
    
    total_mods = len(mod_links)
    
    for i, mod_url in enumerate(mod_links, 1):
        print(f"\n[{i}/{total_mods}] Processing mod...")
        
        # Update progress if callback provided
        if progress_callback:
            progress_callback(i, total_mods)
        
        try:
            result = download_mod_by_url(mod_url, output_dir)
            
            if result['success']:
                successful_downloads.append(result)
                total_storage_bytes += result.get('file_size_mb', 0) * 1024 * 1024
            else:
                failed_downloads.append(result)
                
                # Categorize errors
                error_msg = result.get('error', 'Unknown error')
                if error_msg not in error_categories:
                    error_categories[error_msg] = 0
                error_categories[error_msg] += 1
                
        except Exception as e:
            failed_downloads.append({
                'success': False,
                'mod_name': mod_url.split('/')[-1],
                'error': str(e),
                'manual_url': mod_url
            })
            
            error_msg = str(e)
            if error_msg not in error_categories:
                error_categories[error_msg] = 0
            error_categories[error_msg] += 1
        
        # Add delay between mods to avoid rate limiting
        if i < total_mods:
            time.sleep(1)
    
    # Calculate total storage in MB
    total_storage_mb = round(total_storage_bytes / (1024 * 1024), 2)
    
    # Find most common error
    most_common_error = None
    if error_categories:
        most_common_error = max(error_categories.items(), key=lambda x: x[1])
    
    return {
        'total_mods': total_mods,
        'successful_count': len(successful_downloads),
        'failed_count': len(failed_downloads),
        'successful_downloads': successful_downloads,
        'failed_downloads': failed_downloads,
        'total_storage_mb': total_storage_mb,
        'error_analysis': {
            'error_categories': error_categories,
            'most_common_error': most_common_error[0] if most_common_error else None,
            'most_common_error_count': most_common_error[1] if most_common_error else 0
        }
    }