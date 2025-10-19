import json
import requests
import time
from typing import Union, Dict, List, Any

# Define a type alias for the expected JSON return structure
JSONData = Union[Dict[str, Any], List[Any]]


def get_json_from_url(url: str) -> Union[JSONData, None]:
    """
    Downloads data from a URL, expects a JSON response, and returns the parsed JSON object.

    Args:
        url: The URL of the REST API endpoint.

    Returns:
        A Python dictionary or list (parsed JSON) if successful, otherwise None.
    """
    print(f"Attempting to fetch JSON from: {url}")

    try:
        # Send a GET request. Timeout is good practice.
        response = requests.get(url, timeout=15)

        # Check for HTTP errors (like 404, 500, etc.)
        response.raise_for_status()

        # Attempt to parse the response content as JSON
        data = response.json()

        print(" JSON fetched and parsed successfully.")
        return data

    except requests.exceptions.HTTPError as errh:
        # Check if response exists before accessing .text
        if 'response' in locals() and response.status_code == 404:
            print(f" HTTP Error occurred: {errh}. (URL not found)")
        else:
            print(f" HTTP Error occurred: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f" Connection Error occurred: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f" Timeout Error occurred: {errt}")
    except requests.exceptions.JSONDecodeError:
        # This catches errors if the response is not valid JSON
        print(" Error: Response content is not valid JSON.")
        # Access response text only if the variable exists
        if 'response' in locals():
            print(f"   Raw response text was: {response.text[:100]}...")
    except requests.exceptions.RequestException as err:
        print(f" An unexpected error occurred during the request: {err}")
    except Exception as e:
        print(f" An unexpected error occurred: {e}")

    return None


# --- Main execution block ---
if __name__ == "__main__":
    api_url = "https://visualization.osdr.nasa.gov/biodata/api/v2/datasets/"
    output_filename = "osd-metadata.jsonl"  # Use .jsonl for line-delimited JSON

    # 1. Fetch the main dataset list (which is a dictionary)
    dataset_list = get_json_from_url(api_url)

    if not dataset_list or not isinstance(dataset_list, dict):
        print("\n--- ERROR ---")
        print("Failed to retrieve initial dataset list or it's not a dictionary. Exiting.")
    else:
        print("\n--- Starting Metadata Download ---")
        print(f"Found {len(dataset_list)} datasets. Saving to {output_filename}")

        # 2. Iterate through each dataset entry
        with open(output_filename, "w", encoding="utf-8") as outfile:

            for dataset_id, dataset_info in dataset_list.items():

                # Check if the REST_URL exists before fetching
                if "REST_URL" in dataset_info and dataset_info["REST_URL"]:
                    metadata_url = dataset_info["REST_URL"]

                    # 3. Fetch the detailed metadata using the nested URL
                    metadata = get_json_from_url(metadata_url)

                    if metadata:
                        # 4. Correctly dump the fetched JSON object to the file
                        # We dump it with a newline to create a JSON Lines file (.jsonl)
                        json.dump(metadata, outfile)
                        outfile.write('\n')  # Add newline for JSON Lines format
                        print(f"  --> Saved metadata for Dataset ID: {dataset_id}")
                    else:
                        print(f"  --- Skipping Dataset ID: {dataset_id} (Failed to fetch metadata)")

                # Sleep briefly to be a good API client (avoid rate limiting)
                time.sleep(0.5)

        print("\n--- All Downloads Complete ---")
