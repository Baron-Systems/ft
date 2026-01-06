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

    def _find_bench_path(self, bench_path: Optional[str]) -> Optional[Path]:
        """Find bench path."""
        if bench_path:
            path = Path(bench_path).resolve()
            if path.exists() and (path / "sites").exists():
                return path

        # Try current directory
        cwd = Path.cwd()
        if (cwd / "sites").exists():
            return cwd

        # Try parent directories
        for parent in cwd.parents:
            if (parent / "sites").exists():
                return parent

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

