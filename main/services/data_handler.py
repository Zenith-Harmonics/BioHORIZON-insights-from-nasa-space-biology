import json


def get_latest_papers():
    with open("main/static/data/osd-gpt", encoding="UTF-8") as file:
        metadata = json.load(file)
        paper_list = []
        for key in metadata:
            paper_list.append(
                {
                    "id" : key,
                    "short_title": metadata[key]["short_title"],
                    "short_description": metadata[key]["short_description"]
                }
            )
        print(paper_list)
        return paper_list


def get_paper(osd):
    with open("main/static/data/osd-gpt", encoding="UTF-8") as file:
        metadata = json.load(file)
        paper = metadata[osd]
        return paper