#!/usr/bin/env python3
"""
Phase 2: GitHub repository analyzer for model documentation and code.
Searches GitHub for model repositories, READMEs, and implementation details.
"""
import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime
import sqlite3
from db import get_connection
import re
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitHubAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/vnd.github.v3+json'
        })
        
        # GitHub API token (optional but increases rate limits)
        # Can be set as environment variable GITHUB_TOKEN
        import os
        self.token = os.environ.get('GITHUB_TOKEN')
        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
    
    def search_github_repos(self, model_name, provider):
        """Search GitHub for repositories related to the model."""
        queries = [
            f"{provider} {model_name}",
            f"{model_name} implementation",
            f"{model_name} official"
        ]
        
        repos = []
        for query in queries:
            try:
                # Use GitHub search API
                response = self.session.get(
                    f'https://api.github.com/search/repositories',
                    params={
                        'q': query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': 5
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for repo in data.get('items', []):
                        repos.append({
                            'full_name': repo['full_name'],
                            'html_url': repo['html_url'],
                            'stars': repo['stargazers_count'],
                            'description': repo['description'],
                            'updated_at': repo['updated_at']
                        })
                else:
                    logger.warning(f"GitHub search failed: {response.status_code}")
                    
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error searching GitHub for {query}: {e}")
        
        # Deduplicate repos
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo['full_name'] not in seen:
                seen.add(repo['full_name'])
                unique_repos.append(repo)
        
        return unique_repos[:5]  # Top 5 repos
    
    def analyze_readme(self, repo_full_name):
        """Analyze README file for model information."""
        try:
            # Get README content
            response = self.session.get(
                f'https://api.github.com/repos/{repo_full_name}/readme',
                timeout=10
            )
            
            if response.status_code != 200:
                return {}
            
            data = response.json()
            # Decode base64 content
            content = base64.b64decode(data['content']).decode('utf-8')
            
            # Extract information
            info = {}
            
            # Parameters
            param_match = re.search(r'(\d+\.?\d*)\s*[bt](?:illion)?\s*param', content, re.I)
            if param_match:
                info['parameters'] = f"{param_match.group(1)}B"
            
            # Model architecture
            arch_patterns = [
                r'architecture[:\s]+([^\n]+)',
                r'model\s+type[:\s]+([^\n]+)',
                r'based\s+on\s+([^\n]+)'
            ]
            for pattern in arch_patterns:
                match = re.search(pattern, content, re.I)
                if match:
                    info['architecture'] = match.group(1).strip()
                    break
            
            # Training details
            if 'training data' in content.lower():
                # Extract training data section
                train_match = re.search(r'training\s+data[:\s]+([^\n]+)', content, re.I)
                if train_match:
                    info['training_data'] = train_match.group(1).strip()
            
            # License
            license_match = re.search(r'license[:\s]+([^\n]+)', content, re.I)
            if license_match:
                info['license'] = license_match.group(1).strip()
            
            # Context length
            context_match = re.search(r'(\d+)k?\s*(?:token)?\s*context', content, re.I)
            if context_match:
                info['context_window'] = f"{context_match.group(1)}k"
            
            # Benchmarks
            benchmark_patterns = [
                r'mmlu[:\s]+(\d+\.?\d*)',
                r'humaneval[:\s]+(\d+\.?\d*)',
                r'gsm8k[:\s]+(\d+\.?\d*)'
            ]
            benchmarks = {}
            for pattern in benchmark_patterns:
                match = re.search(pattern, content, re.I)
                if match:
                    benchmark_name = pattern.split('[')[0]
                    benchmarks[benchmark_name] = float(match.group(1))
            if benchmarks:
                info['benchmarks'] = benchmarks
            
            return info
            
        except Exception as e:
            logger.error(f"Error analyzing README for {repo_full_name}: {e}")
            return {}
    
    def analyze_model_config(self, repo_full_name):
        """Look for model configuration files."""
        config_files = ['config.json', 'model_config.json', 'configuration.json']
        
        for config_file in config_files:
            try:
                response = self.session.get(
                    f'https://api.github.com/repos/{repo_full_name}/contents/{config_file}',
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = base64.b64decode(data['content']).decode('utf-8')
                    config = json.loads(content)
                    
                    info = {}
                    
                    # Extract relevant fields
                    if 'hidden_size' in config:
                        info['hidden_size'] = config['hidden_size']
                    if 'num_attention_heads' in config:
                        info['num_attention_heads'] = config['num_attention_heads']
                    if 'num_hidden_layers' in config:
                        info['num_layers'] = config['num_hidden_layers']
                    if 'max_position_embeddings' in config:
                        info['max_sequence_length'] = config['max_position_embeddings']
                    if 'vocab_size' in config:
                        info['vocab_size'] = config['vocab_size']
                    
                    return info
                    
            except Exception as e:
                continue
        
        return {}
    
    def analyze_repository(self, repo):
        """Analyze a single repository for model information."""
        logger.info(f"Analyzing repo: {repo['full_name']}")
        
        info = {
            'repo_url': repo['html_url'],
            'stars': repo['stars'],
            'last_updated': repo['updated_at']
        }
        
        # Analyze README
        readme_info = self.analyze_readme(repo['full_name'])
        info.update(readme_info)
        
        # Analyze config files
        config_info = self.analyze_model_config(repo['full_name'])
        if config_info:
            info['technical_specs'] = config_info
        
        return info
    
    def search_and_analyze(self, model_name, provider):
        """Search GitHub and analyze repositories for a model."""
        # Search for repositories
        repos = self.search_github_repos(model_name, provider)
        
        if not repos:
            logger.warning(f"No GitHub repos found for {provider} {model_name}")
            return []
        
        logger.info(f"Found {len(repos)} repos for {provider} {model_name}")
        
        # Analyze repos in parallel
        all_info = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_repo = {
                executor.submit(self.analyze_repository, repo): repo 
                for repo in repos
            }
            
            for future in as_completed(future_to_repo):
                try:
                    repo_info = future.result()
                    if repo_info and len(repo_info) > 3:  # Has meaningful info
                        all_info.append(repo_info)
                except Exception as e:
                    logger.error(f"Error analyzing repo: {e}")
        
        return all_info

def main():
    """Run GitHub analyzer for models."""
    analyzer = GitHubAnalyzer()
    
    # Get models to analyze
    conn = get_connection()
    cursor = conn.cursor()
    
    # Focus on models missing technical details
    cursor.execute("""
        SELECT name, provider, data 
        FROM models 
        WHERE completeness_percent < 70
        ORDER BY provider, name
    """)
    
    models = cursor.fetchall()
    logger.info(f"Analyzing {len(models)} models on GitHub")
    
    for model_name, provider, data_json in models:
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing {provider} {model_name}")
        
        # Search and analyze GitHub repos
        repo_infos = analyzer.search_and_analyze(model_name, provider)
        
        if repo_infos:
            # Update model data with GitHub findings
            data = json.loads(data_json)
            updated = False
            
            # Aggregate info from all repos
            for repo_info in repo_infos:
                # Update parameters
                if 'parameters' in repo_info and not data.get('properties', {}).get('parameters'):
                    if 'properties' not in data:
                        data['properties'] = {}
                    data['properties']['parameters'] = repo_info['parameters']
                    data['properties']['_filled'] = True
                    updated = True
                    logger.info(f"Found parameters: {repo_info['parameters']}")
                
                # Update architecture
                if 'architecture' in repo_info and not data.get('properties', {}).get('architecture'):
                    if 'properties' not in data:
                        data['properties'] = {}
                    data['properties']['architecture'] = repo_info['architecture']
                    updated = True
                    logger.info(f"Found architecture: {repo_info['architecture']}")
                
                # Update license
                if 'license' in repo_info and not data.get('distribution', {}).get('license_type'):
                    if 'distribution' not in data:
                        data['distribution'] = {}
                    data['distribution']['license_type'] = repo_info['license']
                    data['distribution']['_filled'] = True
                    updated = True
                    logger.info(f"Found license: {repo_info['license']}")
                
                # Update benchmarks
                if 'benchmarks' in repo_info:
                    if 'properties' not in data:
                        data['properties'] = {}
                    data['properties']['benchmarks'] = repo_info['benchmarks']
                    updated = True
                    logger.info(f"Found benchmarks: {repo_info['benchmarks']}")
                
                # Add GitHub source
                if 'sources' not in data:
                    data['sources'] = []
                data['sources'].append({
                    'type': 'github',
                    'url': repo_info['repo_url'],
                    'stars': repo_info['stars']
                })
            
            if updated:
                cursor.execute("""
                    UPDATE models 
                    SET data = ? 
                    WHERE name = ? AND provider = ?
                """, (json.dumps(data), model_name, provider))
                logger.info(f"Updated {model_name} from GitHub data")
        
        # Rate limiting
        time.sleep(3)
    
    conn.commit()
    conn.close()
    logger.info("\nGitHub analysis completed")

if __name__ == "__main__":
    main()