#!/usr/bin/env python3

# Verification script to check if npm package mapping from relationships is working
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'github_sbom_fetcher'))
from fetch_sbom_hierarchy import GitHubSBOMFetcher
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Check if the SBOM file exists
sbom_path = 'sboms/tedg-dev-beatBot-sbom.json'
if not os.path.exists(sbom_path):
    print(f"ERROR: SBOM file not found at {sbom_path}")
    sys.exit(1)

# Load the beatBot SBOM
with open(sbom_path, 'r') as f:
    sbom_data = json.load(f)

print("✅ SBOM loaded successfully")

# Check relationships for npm purls
relationships = sbom_data.get('relationships', [])
npm_relationships = 0
for rel in relationships:
    if rel.get('relationship') == 'DEPENDS_ON':
        related = rel.get('related', '')
        if related.startswith('pkg:npm/'):
            npm_relationships += 1

print(f"✅ Found {npm_relationships} DEPENDS_ON relationships with npm purls")

# Create a mock fetcher to test the mapping
class MockFetcher:
    def __init__(self):
        self.npm_mappings = {
            'express': ('expressjs', 'express'),
            'lodash': ('lodash', 'lodash'),
            'async': ('caolan', 'async'),
            'underscore': ('jashkenas', 'underscore'),
            'request': ('request', 'request'),
            'cheerio': ('cheeriojs', 'cheerio'),
            'debug': ('visionmedia', 'debug'),
            'colors': ('Marak', 'colors.js'),
            'eyes': ('cloudhead', 'eyes.js'),
            'qs': ('ljharb', 'qs')
        }
    
    def _get_github_repo_from_npm(self, package_name, version):
        return self.npm_mappings.get(package_name)

# Test the mapping logic
print("\n✅ Testing npm package mapping from relationships:")
mapped_count = 0
test_count = 0

for rel in relationships[:10]:  # Test first 10 relationships
    if rel.get('relationship') == 'DEPENDS_ON':
        related = rel.get('related', '')
        if related.startswith('pkg:npm/'):
            test_count += 1
            # Extract npm package name
            package_part = related.split('pkg:npm/')[-1]
            decoded_part = package_part  # Skip unquote for test
            parts = decoded_part.split('@')
            if len(parts) >= 1:
                npm_name = parts[0]
                npm_version = parts[1] if len(parts) > 1 else 'latest'
                
                # Test mapping
                mock_fetcher = MockFetcher()
                github_repo = mock_fetcher._get_github_repo_from_npm(npm_name, npm_version)
                if github_repo:
                    dep_owner, dep_repo = github_repo
                    mapped_count += 1
                    print(f"  ✅ Mapped {npm_name}@{npm_version} to {dep_owner}/{dep_repo}")
                else:
                    print(f"  ❌ Could not map {npm_name}@{npm_version}")

print(f"\n✅ Mapped {mapped_count} of {test_count} test npm packages from relationships")

# Now test the actual extraction
print("\n✅ Testing actual dependency extraction:")
try:
    # Create fetcher instance (won't actually fetch)
    fetcher = GitHubSBOMFetcher('dummy_token')
    
    # Extract dependencies
    dependencies = fetcher.extract_dependencies(sbom_data, 'tedg-dev', 'beatBot')
    
    print(f"\n✅ Total dependencies extracted: {len(dependencies)}")
    
    # Count sources
    sources = {}
    for dep in dependencies:
        source = dep.source
        sources[source] = sources.get(source, 0) + 1
    
    print("\n✅ Dependencies by source:")
    for source, count in sources.items():
        print(f"  {source}: {count}")
    
    print("\n✅ First 10 dependencies:")
    for i, dep in enumerate(dependencies[:10]):
        print(f"  {i+1}. {dep.owner}/{dep.repo} (source: {dep.source})")
    
except Exception as e:
    print(f"\n❌ Error during extraction: {e}")
    import traceback
    traceback.print_exc()