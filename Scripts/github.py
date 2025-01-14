from Scripts import resource_fetcher
from Scripts import utils
import random

class Github:
    def __init__(self):
        self.utils = utils.Utils()
        self.fetcher = resource_fetcher.ResourceFetcher()

    def get_latest_release(self, owner, repo):
        url = "https://github.com/{}/{}/releases".format(owner, repo)
        response = self.fetcher.fetch_and_parse_content(url)

        if not response:
            raise ValueError("Failed to fetch release information from GitHub.")

        tag_name = self._extract_tag_name(response)
        body = self._extract_body_content(response)

        release_tag_url = "https://github.com/{}/{}/releases/expanded_assets/{}".format(owner, repo, tag_name)
        response = self.fetcher.fetch_and_parse_content(release_tag_url)

        if not response:
            raise ValueError("Failed to fetch expanded assets information from GitHub.")

        assets = self._extract_assets(response)

        return {
            "body": body,
            "assets": assets
        }

    def _extract_tag_name(self, response):
        for line in response.splitlines():
            if "<a" in line and "href=\"" in line and "/releases/tag/" in line:
                return line.split("/releases/tag/")[1].split("\"")[0]
        return None

    def _extract_body_content(self, response):
        for line in response.splitlines():
            if "<div" in line and "body-content" in line:
                return response.split(line.split(">", 1)[0], 1)[1].split("</div>", 1)[0][1:]
        return ""

    def _extract_assets(self, response):
        assets = []

        for line in response.splitlines():
            if "<a" in line and "href=\"" in line and "/releases/download" in line:
                download_link = line.split("href=\"", 1)[1].split("\"", 1)[0]

                if "tlwm" in download_link or ("tlwm" not in download_link and "DEBUG" not in download_link.upper()):
                    asset_data = response.split(line)[1].split("</div>", 2)[1]
                    asset_id = self._generate_asset_id(asset_data)
                    assets.append({
                        "product_name": self.extract_asset_name(download_link.split("/")[-1]), 
                        "id": int(asset_id), 
                        "url": "https://github.com" + download_link
                    })

        return assets

    def _generate_asset_id(self, asset_data):
        try:
            return "".join(char for char in asset_data.split("datetime=\"")[-1].split("\"")[0][::-1] if char.isdigit())[:9]
        except:
            return "".join(random.choices('0123456789', k=9))
    
    def extract_asset_name(self, file_name):
        end_idx = len(file_name)
        if "." in file_name:
            end_idx = min(file_name.index("."), end_idx)
            if file_name[end_idx] == "." and file_name[end_idx - 1].isdigit():
                end_idx = end_idx - 1
        asset_name = file_name[:end_idx]

        return asset_name