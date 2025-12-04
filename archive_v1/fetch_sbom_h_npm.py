import requests
import re
import csv
import time
from bs4 import BeautifulSoup

GITHUB_DEPS_URL = 'https://github.com/tedg-dev/beatBot/network/dependencies'

def get_dependency_list():
    """Scrape the GitHub network/dependencies page and return a list of (name, version) tuples."""
    resp = requests.get(GITHUB_DEPS_URL)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch {GITHUB_DEPS_URL}: {resp.status_code}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    deps = []
    # On GitHub “Dependency graph” there is a table/list of dependencies with name and version.
    # We need to inspect page structure. We'll assume entries have a pattern like “<a …>cryptiles</a> <span>3.1.2</span>”
    for row in soup.select('li.DependenciesList-item'):  # guess – you may need to adjust selector
        name_el = row.select_one('a.Details-content--dependency-name')
        version_el = row.select_one('span.Details-content--dependency-version')
        if name_el and version_el:
            name = name_el.text.strip()
            version = version_el.text.strip().lstrip('v')  # strip a leading “v” if present
            deps.append((name, version))
    # Fallback: if that selector fails, find all textual patterns like “name@version”
    if not deps:
        for m in re.finditer(r'([a-zA-Z0-9\-\_\/@]+)@([\d\.]+)', resp.text):
            deps.append((m.group(1), m.group(2)))
    return deps

def get_repo_url(pkg_name, version):
    """Query the npm registry for pkg_name@version and attempt to extract the GitHub repository URL."""
    # handle scoped packages
    encoded = pkg_name
    if pkg_name.startswith('@'):
        encoded = pkg_name.replace('/', '%2F')
    url = f'https://registry.npmjs.org/{encoded}/{version}'
    resp = requests.get(url)
    if resp.status_code != 200:
        # fallback to the package without version
        url2 = f'https://registry.npmjs.org/{encoded}'
        resp2 = requests.get(url2)
        if resp2.status_code != 200:
            return None
        meta = resp2.json().get('versions', {}).get(version)
        if not meta:
            return None
    else:
        meta = resp.json()
    repo = meta.get('repository')
    if not repo:
        return None
    if isinstance(repo, dict):
        repo_url = repo.get('url') or repo.get('link')
    else:
        repo_url = repo
    if not repo_url:
        return None
    if repo_url.startswith('git+'):
        repo_url = repo_url[len('git+'):]
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    return repo_url

def main(output_csv='dependencies_with_repos.csv'):
    deps = get_dependency_list()
    print(f"Found {len(deps)} dependencies")
    results = []
    for name, version in deps:
        print(f"Processing: {name}@{version}")
        try:
            repo = get_repo_url(name, version)
        except Exception as e:
            print(f"  Error fetching repo url for {name}@{version}: {e}")
            repo = None
        results.append((name, version, repo))
        time.sleep(0.2)  # throttle
    # write CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name','version','repository_url'])
        for row in results:
            writer.writerow(row)
    print(f"Done. Output written to {output_csv}")

if __name__ == '__main__':
    main()
