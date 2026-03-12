"""
VinylFlow - Discogs Search Worker

Runs Discogs API search + cover art download in a background QThread.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from metadata_handler import MetadataHandler


class SearchWorker(QThread):
    """Background thread for Discogs release search."""

    finished = Signal(list)   # list of (idx, DiscogsRelease)
    error = Signal(str)

    def __init__(self, query: str, token: str, user_agent: str, max_results: int = 5):
        super().__init__()
        self.query = query
        self.token = token
        self.user_agent = user_agent
        self.max_results = max_results

    def run(self):
        try:
            handler = MetadataHandler(self.token, self.user_agent)
            results = handler.search_releases(self.query, max_results=self.max_results)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FetchReleaseWorker(QThread):
    """Background thread to fetch a single Discogs release by ID."""

    finished = Signal(object)  # DiscogsRelease or None
    error = Signal(str)

    def __init__(self, release_id: int, token: str, user_agent: str):
        super().__init__()
        self.release_id = release_id
        self.token = token
        self.user_agent = user_agent

    def run(self):
        try:
            handler = MetadataHandler(self.token, self.user_agent)
            release = handler.get_release_by_id(self.release_id)
            self.finished.emit(release)
        except Exception as e:
            self.error.emit(str(e))


class CoverArtWorker(QThread):
    """Background thread to download cover art for a release."""

    finished = Signal(str, bytes)  # release_id (as str), image data
    error = Signal(str)

    def __init__(self, cover_url: str, release_id: str, user_agent: str):
        super().__init__()
        self.cover_url = cover_url
        self.release_id = release_id
        self.user_agent = user_agent

    def run(self):
        try:
            import requests
            response = requests.get(
                self.cover_url,
                headers={"User-Agent": self.user_agent},
                timeout=15,
            )
            response.raise_for_status()
            self.finished.emit(self.release_id, response.content)
        except Exception as e:
            self.error.emit(str(e))
