#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

GITHUB_WEB = "https://github.com"
GITHUB_API = "https://api.github.com"
SBOM_API = f"{GITHUB_API}/repos/{{owner}}/{{repo}}/dependency-graph/sbom"

_VERSION_RE = re.compile(r"\b\d+\.\d+(?:\.\d+)*(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?\b")

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    owner: str
    repo: str
    version: str


@dataclass
class ProgressState:
    """Track progress of SBOM downloads for resumption."""
    timestamp: str
    base_dir: str
    root_downloaded: bool = False
    completed_repos: Set[str] = field(default_factory=set)
    failed_repos: Set[str] = field(default_factory=set)

    def mark_completed(self, owner: str, repo: str, version: str) -> None:
        key = f"{owner}/{repo}@{version}"
        self.completed_repos.add(key)
        if key in self.failed_repos:
            self.failed_repos.remove(key)

    def mark_failed(self, owner: str, repo: str, version: str) -> None:
        key = f"{owner}/{repo}@{version}"
        self.failed_repos.add(key)

    def is_completed(self, owner: str, repo: str, version: str) -> bool:
        key = f"{owner}/{repo}@{version}"
        return key in self.completed_repos

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "base_dir": self.base_dir,
            "root_downloaded": self.root_downloaded,
            "completed_repos": list(self.completed_repos),
            "failed_repos": list(self.failed_repos),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressState":
        return cls(
            timestamp=data.get("timestamp", ""),
            base_dir=data.get("base_dir", ""),
            root_downloaded=data.get("root_downloaded", False),
            completed_repos=set(data.get("completed_repos", [])),
            failed_repos=set(data.get("failed_repos", [])),
        )


def _resolve_key_path(path: str) -> str:
    """Resolve keys.json path."""
    return path


def load_token(path: str) -> str:
    path = _resolve_key_path(path)
    if not os.path.exists(path):
        raise RuntimeError(f"Credentials file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse credentials JSON: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to read credentials file: {exc}") from exc

    token: Optional[str] = None
    if isinstance(data, dict):
        if "github_token" in data:
            token = str(data["github_token"])
        elif "accounts" in data and isinstance(data["accounts"], list):
            for acc in data["accounts"]:
                if not isinstance(acc, dict):
                    continue
                t = acc.get("token") or acc.get("password")
                if t and t != "<PASTE_TOKEN_HERE>":
                    token = str(t)
                    break
        else:
            t = data.get("token") or data.get("password")
            if t:
                token = str(t)

    if not token:
        raise RuntimeError("No usable token found in credentials file")
    return token


def build_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": (
                "application/vnd.github+json,text/html,"
                "application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-sbom-scraper/1.0",
        }
    )
    return s


def parse_owner_repo(href: str) -> Optional[Tuple[str, str]]:
    if not href:
        return None
    if href.startswith(GITHUB_WEB):
        path = href[len(GITHUB_WEB):]
    else:
        path = href
    if not path.startswith("/"):
        return None
    path = path.split("?", 1)[0].split("#", 1)[0]
    parts = path.strip("/").split("/")
    if len(parts) != 2:
        return None
    owner, repo = parts
    if not owner or not repo:
        return None
    return owner, repo


def extract_dependencies_from_page(
    soup: BeautifulSoup,
    exclude_owner: str = "",
    exclude_repo: str = "",
    page_num: int = 1
) -> List[Dependency]:
    deps: List[Dependency] = []
    seen_entries = set()  # Track owner/repo/version combinations
    skipped_repos = []  # Track what we skip for debugging
    unknown_version_counter = {}  # Count repos without versions
    processed_links = 0

    for a in soup.find_all("a"):
        href = a.get("href") or ""
        parsed = parse_owner_repo(href)
        if not parsed:
            continue
        owner, repo = parsed
        processed_links += 1

        # Skip repos with the same name as target (self-references & forks)
        if exclude_repo and repo.lower() == exclude_repo.lower():
            logger.debug("Skipping same-named repo: %s/%s", owner, repo)
            continue

        # Look for dependency markers and version
        # The structure is: parent div contains repo link + version + label
        # So we need to search parent containers, not just text around link
        parent = a.parent
        version = ""
        has_dep_marker = False

        # Search up to 6 parent levels for the containing structure
        for _ in range(6):
            if parent is None:
                break

            # Get all text in this container (includes siblings)
            if hasattr(parent, "get_text"):
                text = parent.get_text(" ", strip=True)

                # Check for dependency markers
                if "Transitive" in text or "Direct" in text:
                    has_dep_marker = True

                # Try to extract version
                if not version:
                    m = _VERSION_RE.search(text)
                    if m:
                        version = m.group(0)

                # Early exit if we found dependency marker
                if has_dep_marker:
                    break

            parent = parent.parent

        # Only include if we found dependency markers
        if has_dep_marker:
            # Create unique key with owner/repo/version
            # GitHub counts each version separately, even without versions
            if version:
                entry_key = f"{owner.lower()}/{repo.lower()}@{version}"
            else:
                # For entries without versions, use a counter to make each
                # occurrence unique since GitHub counts them separately
                repo_key = f"{owner.lower()}/{repo.lower()}"
                count = unknown_version_counter.get(repo_key, 0)
                unknown_version_counter[repo_key] = count + 1
                entry_key = f"{repo_key}@unknown-{count}"

            # Skip if we've already seen this exact entry on this page
            if entry_key in seen_entries:
                logger.debug("Skipping duplicate: %s/%s @ %s",
                             owner, repo, version or "unknown")
                continue

            seen_entries.add(entry_key)
            deps.append(Dependency(owner=owner, repo=repo, version=version))
            logger.debug("Found dependency: %s/%s @ %s",
                         owner, repo, version or "unknown")
        else:
            # Track repos without dependency markers
            skipped_repos.append(f"{owner}/{repo}")

    # Log summary of skipped repos
    if skipped_repos and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Page %d: Skipped %d repos without dependency markers: %s",
            page_num,
            len(skipped_repos),
            ", ".join(skipped_repos[:10])
        )

    logger.debug(
        "Page %d: Processed %d owner/repo links, extracted %d dependencies",
        page_num,
        processed_links,
        len(deps)
    )
    return deps


def _next_from_html(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    link = soup.find("a", attrs={"rel": "next"})
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    for a in soup.find_all("a"):
        if a.get_text(strip=True) in {"Next", "Next ›"} and a.get("href"):
            return urljoin(base_url, a["href"])
    return None


def scrape_dependencies(
    session: requests.Session,
    owner: str,
    repo: str,
) -> List[Dependency]:
    url = f"{GITHUB_WEB}/{owner}/{repo}/network/dependencies"
    all_deps: List[Dependency] = []
    page = 1
    while url:
        logger.info("Fetching dependency page %d: %s", page, url)
        try:
            resp = session.get(url, timeout=60)
        except requests.RequestException as exc:
            raise RuntimeError(f"Request to {url} failed: {exc}") from exc
        if resp.status_code != 200:
            snippet = resp.text[:200]
            raise RuntimeError(
                f"Failed to load {url}: {resp.status_code} {snippet}"
            )
        soup = BeautifulSoup(resp.text, "html.parser")
        page_deps = extract_dependencies_from_page(soup, owner, repo, page)
        all_deps.extend(page_deps)
        next_url = _next_from_html(soup, url)
        if not next_url:
            break
        url = next_url
        page += 1
        time.sleep(1)
    logger.info("Total dependency entries scraped: %d", len(all_deps))
    return all_deps


def check_rate_limit(response: requests.Response) -> Optional[int]:
    """Check rate limit headers and return seconds to wait if limited."""
    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        # Default wait time for rate limiting
        return 60

    # Check remaining rate limit
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining:
        try:
            if int(remaining) < 5:
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    try:
                        wait_time = int(reset_time) - int(time.time())
                        if wait_time > 0:
                            logger.warning(
                                "Approaching rate limit (%s remaining), "
                                "will wait %d seconds after next request",
                                remaining,
                                wait_time,
                            )
                            return wait_time
                    except ValueError:
                        pass
        except ValueError:
            pass

    return None


def check_dependency_graph_enabled(
    session: requests.Session,
    owner: str,
    repo: str,
) -> bool:
    """Check if dependency graph is enabled for a repository.

    Args:
        session: Requests session
        owner: Repository owner
        repo: Repository name

    Returns:
        True if enabled, False if disabled or cannot be determined
    """
    url = f"{GITHUB_WEB}/{owner}/{repo}/network/dependencies"
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return "Dependency graph is disabled" not in resp.text
    except requests.RequestException:
        pass
    return True  # Assume enabled if we can't check


def fetch_sbom(
    session: requests.Session,
    owner: str,
    repo: str,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """Fetch SBOM with retry logic and rate limit handling.

    Args:
        session: Requests session with auth headers
        owner: Repository owner
        repo: Repository name
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)

    Returns:
        SBOM data as dict, or None if unavailable/failed
    """
    url = SBOM_API.format(owner=owner, repo=repo)
    logger.debug("Fetching SBOM: %s", url)

    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=60)
        except requests.RequestException as exc:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Request for SBOM %s/%s failed (attempt %d/%d): "
                    "%s. Retrying in %.1fs...",
                    owner,
                    repo,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
                continue
            else:
                logger.error(
                    "Request for SBOM %s/%s failed after %d attempts: %s",
                    owner,
                    repo,
                    max_retries,
                    exc,
                )
                return None

        # Check rate limits
        wait_time = check_rate_limit(resp)

        if resp.status_code == 200:
            try:
                return resp.json()
            except json.JSONDecodeError as exc:
                logger.error(
                    "Invalid JSON for SBOM %s/%s: %s",
                    owner,
                    repo,
                    exc,
                )
                return None

        # Don't retry for permanent failures
        if resp.status_code in (403, 404, 202):
            if resp.status_code == 404:
                logger.warning(
                    "SBOM not available for %s/%s: "
                    "Dependency graph likely not enabled (404)",
                    owner,
                    repo,
                )
            elif resp.status_code == 403:
                logger.warning(
                    "SBOM not available for %s/%s: Access forbidden (403)",
                    owner,
                    repo,
                )
            else:  # 202
                logger.warning(
                    "SBOM not available for %s/%s: "
                    "Generation in progress (202)",
                    owner,
                    repo,
                )
            return None

        # Retry for rate limiting (429) and server errors
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < max_retries - 1:
                if wait_time:
                    delay = wait_time
                else:
                    delay = base_delay * (2 ** attempt)

                snippet = resp.text[:200]
                logger.warning(
                    "SBOM request for %s/%s returned %s (attempt "
                    "%d/%d): %s. Retrying in %.1fs...",
                    owner,
                    repo,
                    resp.status_code,
                    attempt + 1,
                    max_retries,
                    snippet,
                    delay,
                )
                time.sleep(delay)
                continue
            else:
                snippet = resp.text[:200]
                logger.error(
                    "SBOM request for %s/%s failed after %d attempts: %s %s",
                    owner,
                    repo,
                    max_retries,
                    resp.status_code,
                    snippet,
                )
                return None

        # Other error codes
        snippet = resp.text[:200]
        logger.error(
            "SBOM request failed for %s/%s: %s %s",
            owner,
            repo,
            resp.status_code,
            snippet,
        )
        return None

    return None


def save_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_error(path: str, message: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(message + "\n")


def save_progress(progress_path: str, state: ProgressState) -> None:
    """Save progress state to disk."""
    try:
        tmp = progress_path + ".tmp"
        os.makedirs(os.path.dirname(progress_path) or ".", exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, progress_path)
        logger.debug("Progress saved to %s", progress_path)
    except Exception as exc:
        logger.error("Failed to save progress: %s", exc)


def load_progress(progress_path: str) -> Optional[ProgressState]:
    """Load progress state from disk."""
    if not os.path.exists(progress_path):
        return None
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = ProgressState.from_dict(data)
        logger.info(
            "Loaded progress: %d completed, %d failed",
            len(state.completed_repos),
            len(state.failed_repos),
        )
        return state
    except Exception as exc:
        logger.warning("Failed to load progress file: %s", exc)
        return None


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Scrape GitHub dependency graph and export SBOMs",
    )
    p.add_argument("--gh-user", required=True, help="GitHub owner/user")
    p.add_argument("--gh-repo", required=True, help="GitHub repository name")
    p.add_argument(
        "--output-dir",
        default="sboms",
        help="Base output directory",
    )
    p.add_argument("--debug", action="store_true", help="Enable debug logging")
    p.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts for failed requests (default: 3)",
    )
    p.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base delay in seconds for exponential backoff (default: 2.0)",
    )
    p.add_argument(
        "--request-delay",
        type=float,
        default=0.5,
        help=("Delay in seconds between requests to avoid rate "
              "limiting (default: 0.5)"),
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous progress (uses latest progress file)",
    )
    args = p.parse_args(argv)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        token = load_token("keys.json")
    except Exception as exc:
        logger.error("Failed to load credentials: %s", exc)
        return 1

    session = build_session(token)

    # Check for existing progress if resuming
    progress_state: Optional[ProgressState] = None
    base_dir: str
    timestamp: str

    if args.resume:
        # Look for most recent progress file
        progress_files = []
        if os.path.exists(args.output_dir):
            for item in os.listdir(args.output_dir):
                if item.startswith("sbom_export_"):
                    progress_path = os.path.join(
                        args.output_dir,
                        item,
                        f"{args.gh_user}_{args.gh_repo}",
                        "progress.json",
                    )
                    if os.path.exists(progress_path):
                        progress_files.append(
                            (os.path.getmtime(progress_path), progress_path)
                        )

        if progress_files:
            progress_files.sort(reverse=True)
            latest_progress = progress_files[0][1]
            logger.info("Attempting to resume from: %s", latest_progress)
            progress_state = load_progress(latest_progress)
            if progress_state:
                base_dir = progress_state.base_dir
                timestamp = progress_state.timestamp
                logger.info("Resuming from previous run at %s", timestamp)
            else:
                logger.warning("Could not load progress, starting fresh")
        else:
            logger.warning("No progress file found, starting fresh")

    if not progress_state:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        base_dir = os.path.join(args.output_dir, f"sbom_export_{timestamp}")
        progress_state = ProgressState(timestamp=timestamp, base_dir=base_dir)

    try:
        deps = scrape_dependencies(session, args.gh_user, args.gh_repo)
    except Exception as exc:
        logger.error("Failed to scrape dependencies: %s", exc)
        return 1

    # Build mapping from repository to all dependency entries referencing it.
    all_by_repo: Dict[Tuple[str, str], List[Dependency]] = {}
    repo_order: List[Tuple[str, str]] = []
    for dep in deps:
        key = (dep.owner.lower(), dep.repo.lower())
        if key not in all_by_repo:
            all_by_repo[key] = []
            repo_order.append(key)
        all_by_repo[key].append(dep)

    unique_deps: List[Dependency] = []
    for key in repo_order:
        # First occurrence for this repo is used for SBOM fetching/filenames.
        unique_deps.append(all_by_repo[key][0])

    total = len(deps)
    unique_total = len(unique_deps)
    duplicate_entries = total - unique_total

    repo_dir = os.path.join(base_dir, f"{args.gh_user}_{args.gh_repo}")
    deps_dir = os.path.join(repo_dir, "dependencies")
    progress_path = os.path.join(repo_dir, "progress.json")

    os.makedirs(deps_dir, exist_ok=True)

    root_sbom_path = os.path.join(
        repo_dir,
        f"{args.gh_user}_{args.gh_repo}-sbom.json",
    )
    root_error_path = os.path.join(
        repo_dir,
        f"{args.gh_user}_{args.gh_repo}-sbom.error.txt",
    )

    api_session = build_session(token)

    # Fetch root SBOM if not already done
    if not progress_state.root_downloaded:
        root_sbom = fetch_sbom(
            api_session,
            args.gh_user,
            args.gh_repo,
            max_retries=args.max_retries,
            base_delay=args.retry_delay,
        )
        if root_sbom:
            try:
                save_json(root_sbom_path, root_sbom)
                logger.info("Saved root SBOM: %s", root_sbom_path)
                progress_state.root_downloaded = True
                save_progress(progress_path, progress_state)
            except Exception as exc:
                logger.error("Failed to save root SBOM: %s", exc)
                save_error(root_error_path, f"Failed to save root SBOM: {exc}")
        else:
            msg = "Root SBOM not available"
            logger.error(msg)
            save_error(root_error_path, msg)
        time.sleep(args.request_delay)
    else:
        logger.info("Root SBOM already downloaded, skipping")

    downloaded = 0
    failed = 0

    for idx, d in enumerate(unique_deps, 1):
        safe_ver = (d.version or "unknown").replace("/", "_").replace(
            "\\", "_",
        )

        # Skip if already completed
        if progress_state.is_completed(
            d.owner, d.repo, d.version or "unknown"
        ):
            logger.info(
                "[%d/%d] Skipping %s/%s@%s (already completed)",
                idx,
                unique_total,
                d.owner,
                d.repo,
                d.version or "?",
            )
            downloaded += 1
            continue

        sbom_path = os.path.join(
            deps_dir,
            f"{d.owner}_{d.repo}_{safe_ver}.json",
        )
        err_path = os.path.join(
            deps_dir,
            f"{d.owner}_{d.repo}_{safe_ver}.error.txt",
        )
        logger.info(
            "[%d/%d] Fetching SBOM for %s/%s@%s",
            idx,
            unique_total,
            d.owner,
            d.repo,
            d.version or "?",
        )
        try:
            sbom = fetch_sbom(
                api_session,
                d.owner,
                d.repo,
                max_retries=args.max_retries,
                base_delay=args.retry_delay,
            )
            if sbom:
                save_json(sbom_path, sbom)
                downloaded += 1
                progress_state.mark_completed(
                    d.owner, d.repo, d.version or "unknown"
                )
                save_progress(progress_path, progress_state)
                logger.debug("  Saved dependency SBOM: %s", sbom_path)
            else:
                # Check if dependency graph is disabled
                if not check_dependency_graph_enabled(
                    session, d.owner, d.repo
                ):
                    logger.warning(
                        "  Dependency graph is disabled for %s/%s",
                        d.owner,
                        d.repo,
                    )
                    save_error(
                        err_path,
                        "Dependency graph is disabled for this repository"
                    )
                else:
                    save_error(
                        err_path, "SBOM not available or request failed"
                    )

                failed += 1
                progress_state.mark_failed(
                    d.owner, d.repo, d.version or "unknown"
                )
                save_progress(progress_path, progress_state)
        except Exception as exc:
            failed += 1
            progress_state.mark_failed(d.owner, d.repo, d.version or "unknown")
            save_progress(progress_path, progress_state)
            msg = f"Exception fetching/saving SBOM: {exc}"
            logger.error("  %s", msg)
            save_error(err_path, msg)

        # Add delay between requests to avoid rate limiting
        time.sleep(args.request_delay)

    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)

    # GitHub comparison callout
    github_ui_count = 229  # Known count for beatBot
    if total != github_ui_count:
        diff = github_ui_count - total
        pct = (total / github_ui_count) * 100
        logger.info("")
        logger.info(
            "GitHub Dependency Graph UI shows %d total dependencies.",
            github_ui_count
        )
        logger.info("Scraped %d entries from HTML (~%.1f%%).", total, pct)
        if diff > 0:
            logger.info("")
            logger.info(
                "Missing %d entries likely due to:",
                diff
            )
            logger.info(
                "  - JavaScript-loaded content not in static HTML"
            )
            logger.info(
                "  - Complex dependency relationships or nested structures"
            )
        logger.info("")

    logger.info("Dependencies scraped: %d", total)
    logger.info("Unique repositories: %d", unique_total)
    logger.info("Duplicate entries skipped: %d", duplicate_entries)
    logger.info("SBOM downloads successful: %d", downloaded)
    logger.info("SBOM downloads failed: %d", failed)
    logger.info("Output directory: %s", os.path.abspath(base_dir))

    print("")
    print(f"Total dependency entries scraped: {total}")
    print(f"Unique repositories: {unique_total}")
    print(f"Duplicate entries skipped: {duplicate_entries}")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed or unavailable: {failed}")
    print(f"Output directory: {os.path.abspath(base_dir)}")

    # Detailed report at the end
    logger.info("\n" + "="*70)
    logger.info("DETAILED REPORT")
    logger.info("="*70)

    # List repositories for which multiple dependency entries were seen.
    duplicate_repos: List[Tuple[str, str, List[Dependency]]] = []
    for key in repo_order:
        entries = all_by_repo[key]
        if len(entries) > 1:
            owner = entries[0].owner
            repo = entries[0].repo
            duplicate_repos.append((owner, repo, entries))

    if duplicate_repos:
        logger.info(
            "\nRepositories with multiple versions detected: %d",
            len(duplicate_repos)
        )
        for owner, repo, entries in duplicate_repos:
            versions = {e.version or "unknown" for e in entries}
            version_list = ", ".join(sorted(versions))
            count = len(entries)
            msg = (
                f"  {owner}/{repo} - {count} versions: {version_list}"
            )
            logger.info(msg)

    logger.info("\n" + "="*70)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        sys.exit(1)
