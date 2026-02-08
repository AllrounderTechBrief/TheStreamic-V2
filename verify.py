#!/usr/bin/env python3
"""
TheStreamic V2 - Verification Script
Run this to verify all changes were applied correctly
"""

import os
import json
import re
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark(passed):
    return f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"

def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def check_file_exists(filename):
    exists = os.path.exists(filename)
    status = check_mark(exists)
    print(f"{status} {filename}")
    return exists

def check_content(filename, search_string, description):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        found = search_string in content
        status = check_mark(found)
        print(f"{status} {description}")
        return found
    except FileNotFoundError:
        print(f"{RED}❌{RESET} {description} - File not found")
        return False

def main():
    print(f"{GREEN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║      TheStreamic V2 - Verification Script                 ║")
    print("║      Date: February 8, 2026                                ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(RESET)
    
    total_checks = 0
    passed_checks = 0
    
    # 1. Check Essential Files
    print_header("Essential Files Check")
    essential_files = [
        'index.html',
        'featured.html',
        'main.js',
        'style.css',
        'data/news.json'
    ]
    
    for file in essential_files:
        total_checks += 1
        if check_file_exists(file):
            passed_checks += 1
    
    # 2. Check Category Pages
    print_header("Category Pages Check")
    category_pages = [
        'playout.html',
        'infrastructure.html',
        'graphics.html',
        'cloud.html',
        'streaming.html',
        'audio-ai.html'
    ]
    
    for file in category_pages:
        total_checks += 1
        if check_file_exists(file):
            passed_checks += 1
    
    # 3. Check Cache-Busting
    print_header("Cache-Busting Implementation")
    for page in ['featured.html', 'playout.html', 'cloud.html']:
        total_checks += 1
        if check_content(page, 'main.js?v=20260208', f"{page}: Cache-busted script tag"):
            passed_checks += 1
    
    # 4. Check Navigation Updates
    print_header("Navigation Updates")
    for page in ['featured.html', 'playout.html', 'cloud.html']:
        total_checks += 1
        if check_content(page, 'FEATURED', f"{page}: FEATURED in navigation"):
            passed_checks += 1
        
        total_checks += 1
        if check_content(page, 'CLOUD PRODUCTION', f"{page}: CLOUD PRODUCTION in navigation"):
            passed_checks += 1
    
    # 5. Check Index Redirect
    print_header("Index Page Redirect")
    total_checks += 1
    if check_content('index.html', 'featured.html', "index.html: Redirects to featured.html"):
        passed_checks += 1
    
    # 6. Check main.js Updates
    print_header("Main.js Updates")
    total_checks += 1
    if check_content('main.js', 'featured', "main.js: Featured category logic"):
        passed_checks += 1
    
    total_checks += 1
    if check_content('main.js', 'cloud-production', "main.js: Cloud Production category"):
        passed_checks += 1
    
    total_checks += 1
    if check_content('main.js', 'fm=webp', "main.js: WebP fallback images"):
        passed_checks += 1
    
    total_checks += 1
    if check_content('main.js', 'Date.now()', "main.js: Cache-busting for news.json"):
        passed_checks += 1
    
    # 7. Check Cloud.html Specifics
    print_header("Cloud Production Page Updates")
    total_checks += 1
    if check_content('cloud.html', 'Cloud Production - The Streamic', "cloud.html: Updated page title"):
        passed_checks += 1
    
    total_checks += 1
    if check_content('cloud.html', '<h1 class="category-heading">Cloud Production</h1>', 
                    "cloud.html: Updated heading"):
        passed_checks += 1
    
    # 8. Check Data File
    print_header("Data File Verification")
    try:
        with open('data/news.json', 'r') as f:
            data = json.load(f)
        
        total_checks += 1
        if len(data) > 0:
            passed_checks += 1
            print(f"{GREEN}✅{RESET} news.json: Contains {len(data)} articles")
        else:
            print(f"{RED}❌{RESET} news.json: Empty or invalid")
        
        # Check categories
        categories = {}
        for item in data:
            cat = item.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n{BLUE}Category Distribution:{RESET}")
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count} articles")
        
    except Exception as e:
        print(f"{RED}❌{RESET} Error reading news.json: {e}")
    
    # 9. Final Summary
    print_header("Verification Summary")
    
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {GREEN}{passed_checks}{RESET}")
    print(f"Failed: {RED}{total_checks - passed_checks}{RESET}")
    print(f"Success Rate: {GREEN if percentage >= 95 else YELLOW}{percentage:.1f}%{RESET}")
    
    if percentage >= 95:
        print(f"\n{GREEN}{'=' * 60}{RESET}")
        print(f"{GREEN}✅ VERIFICATION PASSED - READY FOR DEPLOYMENT!{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}\n")
        return 0
    else:
        print(f"\n{YELLOW}{'=' * 60}{RESET}")
        print(f"{YELLOW}⚠️  SOME CHECKS FAILED - REVIEW ABOVE ERRORS{RESET}")
        print(f"{YELLOW}{'=' * 60}{RESET}\n")
        return 1

if __name__ == "__main__":
    exit(main())
