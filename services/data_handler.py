import json
import gpt_agent

class Data:
    def __init__(self):
        self.gpt = gpt_agent.Summarizer()
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

    def get_latest_research(self, index):
        latest_research = {}
        research_titles = self.datasets_metadata.keys()

        research_titles = [str(k) for k in research_titles]

        for i in range(0, index + 1):
            [osd] = self.datasets_metadata[research_titles[i]].keys()
            latest_research[research_titles[i]] = self.gpt.summarize(self.datasets_metadata[research_titles[i]][osd]["metadata"]["study description"])
        return latest_research


# Example usage
#data = Data()

#lol = data.search_datasets_metadata_by_keywords(["mice"])

#print(data.get_description_from_metadata(lol[0]))
# print(data.get_description_from_metadata(lol[0]))

#print(data.get_latest_research(0))

#gpt = gpt_agent.Summarizer()

#print(gpt.summarize("asudhauisdhdas"))