import os
import json
import re
import csv

reg = re.compile(r"[^\:\(\)]+")


def generate_prompt_map(data, extract_prompt):
    prompt_map = {}
    for i in range(len(data)):
        prompt = extract_prompt(data[i])
        if prompt:
            for w in prompt.split(','):
                if not w:
                    continue
                w = w.strip()
                searchResult = re.search(reg, w)
                if searchResult:
                    prompt = searchResult.group()
                    if prompt not in prompt_map:
                        prompt_map[prompt] = 1
                    else:
                        prompt_map[prompt] += 1
    if len(prompt_map.keys()) > 0:
        return prompt_map
    else:
        return None


def save_prompt_map(data, filename):
    f = open(filename, "w")
    csv_writer = csv.writer(f)
    csv_writer.writerow(["prompt", "count"])
    prompt_list = [[key, data[key]] for key in data.keys()]
    csv_writer.writerows(prompt_list)
    f.close()


data_file = os.path.join(os.path.dirname(__file__), "../../data/civitai_images.json")
f = open(data_file, "r")
content = f.read()
json = json.loads(content)

np_map = generate_prompt_map(
    json, lambda d: d.get("meta").get("negativePrompt") if d.get("meta") else None
)
if np_map:
    csv_file = os.path.join(
        os.path.dirname(__file__), "../../data/civitai_negative_prompt.csv"
    )
    save_prompt_map(np_map, csv_file)

p_map = generate_prompt_map(
    json, lambda d: d.get("meta").get("prompt") if d.get("meta") else None
)
if p_map:
    csv_file = os.path.join(os.path.dirname(__file__), "../../data/civitai_prompt.csv")
    save_prompt_map(p_map, csv_file)
