import os
import json
import time
from typing import Dict, Any, Union, List
from openai import OpenAI
from openai import APIError

# --- OpenAI Client Initialization ---
try:
    # Client automatically picks up the OPENAI_API_KEY environment variable
    CLIENT = OpenAI()
except Exception as e:
    print("FATAL ERROR: Could not initialize OpenAI client.")
    print("Please ensure the OPENAI_API_KEY environment variable is set.")
    exit(1)


def generate_enhanced_json(data_id: str, study_title: str, study_description: str, original_metadata: Dict) -> Union[
    Dict[str, Any], None]:
    """
    Calls the GPT API to generate a short title, summary, key findings, and classification tags
    based on the study metadata.

    Returns the generated content as a Python dictionary.
    """

    # 1. Define the GPT system instruction
    system_instruction = (
        "You are an expert NASA GeneLab data curator. Your task is to analyze the complex study metadata "
        "and generate public-facing summaries PLUS strictly classify the study into provided categories. "
        "The output MUST be a single JSON object. DO NOT include any text outside the JSON object. "
        "The short_title MUST be 5-9 words. The key_findings MUST be a list of 3-5 bullet points. "
        "The summary should be 3-5 sentences. The description should be 6-8 sentences."
        "For classification tags, choose only one best-fit option for each category."
    )

    # Extract original data points for better context and classification guidance
    organism = original_metadata.get("organism", "Unknown Organism")
    study_type = original_metadata.get("project type", "Unknown Type")
    assay_type = original_metadata.get("study assay technology type", "Unknown Assay")

    # 2. Define the user prompt, including the expected output structure and classification constraints
    user_prompt = f"""
    Analyze the following study metadata and generate the required content in the exact JSON format specified below.

    Context:
    - Organism: {organism}
    - Study Type: {study_type}
    - Assay Type: {assay_type}
    - Study Title: "{study_title}"
    - Study Description: "{study_description}"

    Classification Categories (Select ONE for each of the first four categories):
    Data Source: [CGene, ALSDA, ESA]
    Organism / Model: [Human, Rodent, Invertebrate (e.g., Fly), Plant, Cell Culture]
    Mission / Platform: [International Space Station (ISS), Space Shuttle, Terrestrial (Ground Control), Modeled Microgravity]
    Experiment Type: [Transcriptomics (Gene Expression), Proteomics, Metabolomics, Imaging / Visual, Physiological]

    Target JSON Format:
    {{
        "short_title": "[5-9 word, catchy title]",
        "short_summary": [14-20 words],
        "summary": "[3-5 sentence public-facing summary]",
        "description": "[6-8 sentence detailed public-facing description]",
        "key_findings": [
            "[3-5 key bullet point findings]",
            "..."
        ],
        "data_source_category": "[Selected Data Source]",
        "organism_category": "[Selected Organism / Model]",
        "mission_category": "[Selected Mission / Platform]",
        "experiment_type_category": "[Selected Experiment Type]"
    }}
    """

    print(f"  -> Sending prompt for {data_id}...")

    try:
        response = CLIENT.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Low temperature for reliable classification
            response_format={"type": "json_object"}
        )

        json_string = response.choices[0].message.content.strip()
        generated_data = json.loads(json_string)

        print(f"  -> ✅ GPT data generated for {data_id}.")
        return generated_data

    except APIError as e:
        print(f"OpenAI API Error for {data_id}: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error for {data_id}: Could not parse model output: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for {data_id}: {e}")

    return None


def process_metadata_file(input_filename: str, output_filename: str):
    """Reads input JSONL, fetches GPT data, merges, and writes to output JSONL."""

    total_processed = 0
    total_successful = 0

    print(f"Reading from: {input_filename}")
    print(f"Writing enhanced data to: {output_filename}\n")

    with open(input_filename, 'r', encoding='utf-8') as infile, \
            open(output_filename, 'w', encoding='utf-8') as outfile:

        for line in infile:
            if not line.strip():
                continue

            try:
                original_data = json.loads(line)

                dataset_id = next(iter(original_data.keys()))
                dataset_info = original_data[dataset_id]
                original_meta = dataset_info.get("metadata", {})

                total_processed += 1

                # Extract necessary fields for the prompt and final output
                study_title = original_meta.get("study title", "N/A")
                study_description = original_meta.get("study description", "No description provided.")

                if study_title == "N/A":
                    print(f"  -> Skipping {dataset_id}: Missing study title.")
                    continue

                # 1. Call the GPT function to get summaries and CLASSIFICATIONS
                enhanced_data = generate_enhanced_json(dataset_id, study_title, study_description, original_meta)

                # 2. Merge and Save
                if enhanced_data:
                    # Construct the final desired output structure, merging GPT and original data
                    final_output = {
                        dataset_id: {
                            **enhanced_data,  # GPT-generated fields (including classifications)
                            "study_publication_title": original_meta.get("study publication title", "N/A"),
                            "start_date": original_meta.get("mission", {}).get("start date", "Unknown"),
                            "end_date": original_meta.get("mission", {}).get("end date", "Unknown"),
                            # Preserve original link data
                            "data_source_original": original_meta.get("data source type", "N/A"),
                            "project_link": original_meta.get("project link", "N/A"),
                            "files": dataset_info.get("files", {}).get("REST_URL", "N/A")
                        }
                    }

                    json.dump(final_output, outfile)
                    outfile.write('\n')
                    total_successful += 1

                time.sleep(1)  # Wait 1 second between requests

            except Exception as e:
                print(f"Fatal error processing line {total_processed}: {e}")

    print("\n--- Processing Complete ---")
    print(f"Total datasets processed: {total_processed}")
    print(f"Total successful enhancements: {total_successful}")


if __name__ == "__main__":
    # --- TEMPORARY DATA SETUP ---
    # This block creates the required input file based on the JSON you provided.
    INPUT_FILE = "osd-metadata.jsonl"
    OUTPUT_FILE = "enhanced_osd_metadata.jsonl"

    # Paste the JSON lines you provided here for testing:
    temp_data = """
    {"OSD-1": {"REST_URL": "...", "files": {"REST_URL": "https://.../OSD-1/files/"}, "metadata": {"mission": {"end date": "07/17/2006", "start date": "07/04/2006", "name": "STS-121"}, "material type": "Whole Organism", "study title": "Expression data from drosophila melanogaster", "study description": "Space travel presents unlimited opportunities for exploration and discovery, but requires a more complete understanding of the immunological consequences of long-term exposure to the conditions of spaceflight. We used the Drosophila model to compare innate immune responses to bacteria and fungi in flies that were either raised on earth or in outer space aboard the NASA Space Shuttle Discovery (STS-121).", "study assay technology type": "DNA microarray", "project type": "Spaceflight Study", "data source type": "cgene", "study publication title": "Toll Mediated Infection Response Is Altered by Gravity and Spaceflight in Drosophila", "organism": "Drosophila melanogaster", "project link": "https://lsda.jsc.nasa.gov/scripts/experiment/exper.aspx?exp_index=13676"}}}
    {"OSD-2": {"REST_URL": "...", "files": {"REST_URL": "https://.../OSD-2/files/"}, "metadata": {"mission": {"end date": "", "start date": "", "name": ""}, "material type": "Cells", "study title": "Response of human lymphoblastoid cells to HZE (iron ions) or gamma-rays", "study description": "Transcriptional profiling of human lymphoblastoid TK6 cells comparing mock irradiated cells with cells exposed 24 hours previously to 1.67 Gy HZE or 2.5 Gy 137Cs gamma rays. The goal was to understand functional genomic and signaling responses to HZE particle radiation.", "study assay technology type": "DNA microarray", "project type": "Ground Study", "data source type": "cgene", "study publication title": "p53-independent downregulation of histone gene expression in human cell lines by high- and low-let radiation.", "organism": "Homo sapiens", "project link": "http://lsda.jsc.nasa.gov/scripts/experiment/exper.aspx?exp_index=10327"}}}
    """



    # --- Execute the main processing function ---
    process_metadata_file(INPUT_FILE, OUTPUT_FILE)