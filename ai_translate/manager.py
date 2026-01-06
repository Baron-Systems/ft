"""Frappe app and bench utilities."""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Set

from ai_translate.output import OutputFilter


class BenchManager:
    """Manager for Frappe bench operations."""

    def __init__(self, bench_path: Optional[str] = None, output: Optional[OutputFilter] = None):
        """
        Initialize bench manager.

        Args:
            bench_path: Path to bench directory
            output: Output filter instance
        """
        self.output = output or OutputFilter()
        self.bench_path = self._find_bench_path(bench_path)
        self.apps_path = self.bench_path / "apps" if self.bench_path else None
        self.sites_path = self.bench_path / "sites" if self.bench_path else None

    def _find_frappe_manager_benches(self) -> List[Path]:
        """
        Find benches using Frappe Manager (fm).

        Returns:
            List of bench paths found via fm
        """
        benches = []
        benches_set = set()  # To avoid duplicates
        
        try:
            # Try 'fm bench list' first (if it exists)
            result = subprocess.run(
                ["fm", "bench", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse output: format is usually "bench-name -> /path/to/bench"
                for line in result.stdout.splitlines():
                    if "->" in line:
                        parts = line.split("->")
                        if len(parts) == 2:
                            bench_path = Path(parts[1].strip())
                            if bench_path.exists() and (bench_path / "sites").exists():
                                benches_set.add(bench_path.resolve())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception:
            pass
        
        # Try 'fm list' to get sites and extract bench paths
        try:
            result = subprocess.run(
                ["fm", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse table output - look for Path column
                for line in result.stdout.splitlines():
                    # Look for paths that contain "sites"
                    if "/sites/" in line or "/frappe/" in line:
                        # Extract path from line
                        parts = line.split()
                        for part in parts:
                            if "/sites/" in part or "/frappe/" in part:
                                site_path = Path(part.strip())
                                if site_path.exists():
                                    # Frappe Manager structure:
                                    # Site path: /home/baron/frappe/sites/site-name
                                    # Bench path: /home/baron/frappe/sites/site-name/workspace/frappe-bench
                                    
                                    # First, check if this is a site directory with workspace/frappe-bench
                                    workspace_bench = site_path / "workspace" / "frappe-bench"
                                    if workspace_bench.exists() and (workspace_bench / "sites").exists() and (workspace_bench / "apps").exists():
                                        benches_set.add(workspace_bench.resolve())
                                        continue
                                    
                                    # Also check if site_path itself is a site directory
                                    if site_path.name != "sites" and "sites" in str(site_path):
                                        # Try workspace/frappe-bench pattern
                                        workspace_bench2 = site_path / "workspace" / "frappe-bench"
                                        if workspace_bench2.exists() and (workspace_bench2 / "sites").exists() and (workspace_bench2 / "apps").exists():
                                            benches_set.add(workspace_bench2.resolve())
                                    
                                    # Legacy: Try parent directory (for non-Frappe Manager setups)
                                    potential_bench = site_path.parent  # /home/baron/frappe
                                    if (potential_bench / "sites").exists() and (potential_bench / "apps").exists():
                                        benches_set.add(potential_bench.resolve())
                                    
                                    # Try frappe-bench pattern
                                    bench_name = potential_bench.name
                                    if bench_name == "frappe":
                                        potential_bench2 = potential_bench.parent / "frappe-bench"  # /home/baron/frappe-bench
                                        if potential_bench2.exists() and (potential_bench2 / "sites").exists() and (potential_bench2 / "apps").exists():
                                            benches_set.add(potential_bench2.resolve())
                                    
                                    # Also check if parent's parent is bench
                                    potential_bench3 = potential_bench.parent
                                    if (potential_bench3 / "sites").exists() and (potential_bench3 / "apps").exists():
                                        benches_set.add(potential_bench3.resolve())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception:
            pass
        
        # Convert set to list and validate
        for bench_path in benches_set:
            if bench_path.exists() and (bench_path / "sites").exists() and (bench_path / "apps").exists():
                benches.append(bench_path)
                self.output.info(f"Found Frappe Manager bench: {bench_path}", verbose_only=True)
        
        return benches

    def _find_bench_path(self, bench_path: Optional[str]) -> Optional[Path]:
        """
        Find bench path with Frappe Manager support.

        Args:
            bench_path: Explicit bench path (if provided)

        Returns:
            Bench path or None
        """
        # 1. Use explicit path if provided
        if bench_path:
            path = Path(bench_path).resolve()
            if path.exists() and (path / "sites").exists() and (path / "apps").exists():
                self.output.info(f"Using provided bench path: {path}", verbose_only=True)
                return path
            else:
                self.output.warning(f"Provided bench path not found or invalid: {bench_path}")
                if path.exists():
                    missing = []
                    if not (path / "sites").exists():
                        missing.append("sites")
                    if not (path / "apps").exists():
                        missing.append("apps")
                    if missing:
                        self.output.warning(f"Missing directories: {', '.join(missing)}")

        # 2. Try Frappe Manager benches
        fm_benches = self._find_frappe_manager_benches()
        if fm_benches:
            # Use the first bench found (or could prompt user)
            self.output.info(f"Using Frappe Manager bench: {fm_benches[0]}", verbose_only=True)
            return fm_benches[0]

        # 3. Try current directory
        cwd = Path.cwd()
        if (cwd / "sites").exists() and (cwd / "apps").exists():
            self.output.info(f"Using current directory as bench: {cwd}", verbose_only=True)
            return cwd

        # 4. Try parent directories
        for parent in cwd.parents:
            if (parent / "sites").exists() and (parent / "apps").exists():
                self.output.info(f"Found bench in parent directory: {parent}", verbose_only=True)
                return parent

        # 5. Try to extract bench from Frappe Manager site paths
        try:
            result = subprocess.run(
                ["fm", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse output to find site paths and extract bench
                for line in result.stdout.splitlines():
                    if "/sites/" in line or "/frappe/" in line:
                        parts = line.split()
                        for part in parts:
                            if "/sites/" in part:
                                site_path = Path(part.strip())
                                if site_path.exists():
                                    # Frappe Manager structure:
                                    # Site path: /home/baron/frappe/sites/site-name
                                    # Bench path: /home/baron/frappe/sites/site-name/workspace/frappe-bench
                                    
                                    # First, check workspace/frappe-bench pattern (Frappe Manager)
                                    workspace_bench = site_path / "workspace" / "frappe-bench"
                                    if workspace_bench.exists() and (workspace_bench / "sites").exists() and (workspace_bench / "apps").exists():
                                        self.output.info(f"Found bench from Frappe Manager (workspace/frappe-bench): {workspace_bench}", verbose_only=True)
                                        return workspace_bench.resolve()
                                    
                                    # Legacy: Try parent directory (for non-Frappe Manager setups)
                                    potential_bench = site_path.parent  # /home/baron/frappe
                                    if (potential_bench / "sites").exists() and (potential_bench / "apps").exists():
                                        self.output.info(f"Found bench from Frappe Manager site: {potential_bench}", verbose_only=True)
                                        return potential_bench.resolve()
                                    
                                    # Try frappe-bench pattern
                                    bench_name = potential_bench.name  # "frappe"
                                    if bench_name == "frappe":
                                        potential_bench2 = potential_bench.parent / "frappe-bench"  # /home/baron/frappe-bench
                                        if potential_bench2.exists() and (potential_bench2 / "sites").exists() and (potential_bench2 / "apps").exists():
                                            self.output.info(f"Found bench from Frappe Manager (frappe-bench pattern): {potential_bench2}", verbose_only=True)
                                            return potential_bench2.resolve()
                                    
                                    # Try parent's parent
                                    potential_bench3 = potential_bench.parent
                                    if (potential_bench3 / "sites").exists() and (potential_bench3 / "apps").exists():
                                        self.output.info(f"Found bench from Frappe Manager site (parent): {potential_bench3}", verbose_only=True)
                                        return potential_bench3.resolve()
        except Exception:
            pass
        
        # 6. Try common Frappe Manager locations
        common_paths = [
            Path.home() / "frappe-bench",
            Path.home() / "frappe",
            Path("/home/frappe/frappe-bench"),
            Path("/home/frappe/frappe"),
            Path("/opt/frappe/frappe-bench"),
            Path("/opt/frappe/frappe"),
        ]
        for path in common_paths:
            if path.exists() and (path / "sites").exists() and (path / "apps").exists():
                self.output.info(f"Found bench in common location: {path}", verbose_only=True)
                return path

        return None

    def get_apps(self, app_names: Optional[List[str]] = None, all_apps: bool = False) -> List[str]:
        """
        Get list of apps to process.

        Args:
            app_names: Specific app names
            all_apps: Include all apps

        Returns:
            List of app names
        """
        if not self.apps_path or not self.apps_path.exists():
            self.output.warning("Apps directory not found")
            return []

        if all_apps:
            apps = [
                d.name
                for d in self.apps_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            return sorted(apps)

        if app_names:
            # Validate apps exist
            valid_apps = []
            for app in app_names:
                app_path = self.apps_path / app
                if app_path.exists():
                    valid_apps.append(app)
                else:
                    self.output.warning(f"App '{app}' not found")
            return valid_apps

        return []

    def get_site_path(self, site_name: str) -> Optional[Path]:
        """
        Get site path.

        Args:
            site_name: Site name

        Returns:
            Site path or None
        """
        if not self.sites_path:
            return None
        site_path = self.sites_path / site_name
        if site_path.exists():
            return site_path
        return None

    def get_app_path(self, app_name: str) -> Optional[Path]:
        """
        Get app path.

        Args:
            app_name: App name

        Returns:
            App path or None
        """
        if not self.apps_path:
            return None
        app_path = self.apps_path / app_name
        if app_path.exists():
            return app_path
        return None

    def get_locale_path(self, site_name: str, lang: str) -> Optional[Path]:
        """
        Get locale path for site and language.

        Args:
            site_name: Site name
            lang: Language code

        Returns:
            Locale path or None
        """
        site_path = self.get_site_path(site_name)
        if not site_path:
            return None
        locale_path = site_path / "assets" / "locale" / lang / "LC_MESSAGES"
        locale_path.mkdir(parents=True, exist_ok=True)
        return locale_path

    def get_frappe_version(self) -> Optional[str]:
        """Get Frappe version."""
        frappe_path = self.get_app_path("frappe")
        if not frappe_path:
            return None

        setup_py = frappe_path / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                # Simple extraction
                for line in content.splitlines():
                    if "version" in line.lower() and "=" in line:
                        version = line.split("=")[-1].strip().strip('"').strip("'")
                        return version
            except Exception:
                pass

        return None

    def run_bench_command(self, command: List[str], site: Optional[str] = None) -> bool:
        """
        Run bench command.

        Args:
            command: Command arguments
            site: Site name (optional)

        Returns:
            True if successful
        """
        if not self.bench_path:
            return False

        cmd = ["bench", "--site", site] if site else ["bench"]
        cmd.extend(command)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.bench_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                self.output.error(f"Command failed: {' '.join(cmd)}")
                if result.stderr:
                    self.output.error(result.stderr)
                return False
            return True
        except Exception as e:
            self.output.error(f"Error running command: {e}")
            return False

