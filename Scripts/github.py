from Scripts import resource_fetcher
from Scripts import utils

class Github:
    def __init__(self):
        self.utils = utils.Utils()
        # Set the headers for GitHub API requests
        self.headers = {
            "Accept": "application/vnd.github+json",
            "#Authorization": "token GITHUB_TOKEN",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.fetcher = resource_fetcher.ResourceFetcher(self.headers)

    def get_latest_release(self, owner, repo):
        url = "https://api.github.com/repos/{}/{}/releases".format(owner, repo)

        response = self.fetcher.fetch_and_parse_content(url, "json")
        
        try:
            latest_release = response[0]
        except:
            return
        
        if not isinstance(latest_release, dict):
            return
        
        assets = []

        for asset in response[0].get("assets"):
            asset_id = asset.get("id")
            download_url = asset.get("browser_download_url")
            asset_name = self.extract_asset_name(asset.get("name"))

            if "tlwm" in download_url or ("tlwm" not in download_url and "DEBUG" not in download_url.upper()):
                assets.append({
                    "product_name": asset_name, 
                    "id": asset_id, 
                    "url": download_url
                })

        return {
            "describe": latest_release.get("body"),
            "assets": assets
        }
    
    def extract_asset_name(self, file_name):
        end_idx = len(file_name)
        if "." in file_name:
            end_idx = min(file_name.index("."), end_idx)
            if file_name[end_idx] == "." and file_name[end_idx - 1].isdigit():
                end_idx = end_idx - 1
        asset_name = file_name[:end_idx]

        return asset_name