import json


class Data:
    def __init__(self):
        self.path = ""
        self.filename = "datasets_metadata.json"
        self.datasets_metadata = {}

        with open(self.path + self.filename, "r") as file:
            self.datasets_metadata = json.load(file)

    def set_path(self, path):
        self.path = path

    def set_filename(self, filename):
        self.filename = filename

    def get_datasets_metadata(self):
        return self.datasets_metadata

    def search_datasets_metadata_by_keywords(self, keywords):
        results = []
        
        for dataset_metadata_name in self.datasets_metadata.keys():
            for keyord in keywords:
                if keyord.lower() in dataset_metadata_name.lower():
                    results.append(self.datasets_metadata[dataset_metadata_name])
                    break

        return results

    def get_description_from_metadata(self, metadata):
        osd_name = next(iter(metadata))
        return metadata[osd_name]["metadata"]["study description"]

# Example usage
data = Data()


lol = data.search_datasets_metadata_by_keywords(["mice"])

print(data.get_description_from_metadata(lol[0]))