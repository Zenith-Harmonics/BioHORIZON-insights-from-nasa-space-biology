import json
import os
from django.conf import settings


class ExperimentDataHandler:
    """
    A singleton class to load and manage experiment data from a JSONL file.
    """
    _instance = None
    _data_loaded = False
    experiments = {}

    def __new__(cls):
        """Ensures only one instance of the class is created (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(ExperimentDataHandler, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
        """Loads data from the JSONL file into the in-memory 'experiments' dictionary."""
        if self._data_loaded:
            return

        # Filename confirmed as enhanced_osd_metadata.jsonl (with underscore)
        file_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'enhanced_osd_metadata.jsonl')

        if not os.path.exists(file_path):
            # Print a clear error message if the file is not found
            print("-" * 50)
            print("DATA LOAD ERROR: Experiment data file not found!")
            print(f"EXPECTED PATH: {file_path}")
            print("Please ensure the file exists at this exact location.")
            print("-" * 50)
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        line_data = json.loads(line.strip())
                        # The key is the OSD ID, the value is the experiment data
                        osd_id, exp_data = next(iter(line_data.items()))
                        self.experiments[osd_id] = exp_data

                        # Ensure key_findings is a list
                        kf = self.experiments[osd_id].get('key_findings')
                        if kf and isinstance(kf, str):
                            self.experiments[osd_id]['key_findings'] = [kf]

                    except Exception as e:
                        print(f"Error processing line (Skipped): {line.strip()[:50]}... - {e}")
                        continue
        except Exception as file_error:
            print(f"FATAL FILE READ ERROR: Could not open or read file: {file_path}. Error: {file_error}")
            return

        self._data_loaded = True
        if len(self.experiments) > 0:
            print(f"INFO: Loaded {len(self.experiments)} experiments successfully: {len(self.experiments)} records.")
        else:
            print("WARNING: Data file was found, but 0 experiments were loaded. Check file format.")

    # ------------------ Query Methods ------------------

    def get_experiment_by_id(self, osd_id):
        """Returns a single experiment by its OSD-ID."""
        return self.experiments.get(osd_id)

    def search_experiments(self, keyword=None, filters=None):
        """
        Searches and filters experiments based on keywords and categories.

        This method now safely converts potential list fields (like publication title)
        to strings before comparison to avoid 'list' object has no attribute 'lower'.
        """
        results = []
        keyword = keyword.lower() if keyword else ''
        filters = filters or {}

        for exp_id, exp in self.experiments.items():

            # 1. Filter check
            filter_match = True
            for key, required_value in filters.items():
                if required_value and exp.get(key) != required_value:
                    filter_match = False
                    break

            if not filter_match:
                continue

            # 2. Keyword check
            keyword_match = True
            if keyword:

                # Helper function to convert any field to a searchable string
                def safe_to_string(value):
                    if isinstance(value, list):
                        return " ".join(map(str, value))  # Join list elements into a single string
                    return str(value)  # Convert everything else to a string

                search_fields = [
                    exp.get('short_title', ''),
                    exp.get('summary', ''),
                    exp.get('description', ''),
                    exp.get('organism_category', ''),
                    # CRITICAL FIX HERE: Explicitly pass the publication title through the safe converter
                    safe_to_string(exp.get('study_publication_title', '')),
                    # Key findings are already a list, joined here
                    " ".join(exp.get('key_findings', [])),
                ]

                # Check if the keyword is in any of the search fields (case-insensitive)
                if not any(keyword in field.lower() for field in search_fields if field):
                    keyword_match = False

            if keyword_match:
                exp_with_id = {'osd_id': exp_id, **exp}
                results.append(exp_with_id)

        return results

    def get_unique_filter_values(self):
        """Returns a dictionary of all unique values for filter categories."""
        unique_values = {
            'organism_category': set(), 'mission_category': set(),
            'experiment_type_category': set(), 'data_source_category': set(),
        }

        for exp in self.experiments.values():
            for category in unique_values.keys():
                value = exp.get(category)
                if value:
                    unique_values[category].add(value)

        return {k: sorted(list(v)) for k, v in unique_values.items()}


# MANDATORY: Initialize the handler once at the end of the module
data_handler = ExperimentDataHandler()
