# tests/test_utilities.py
import unittest
import os
import shutil
import json
import yaml
from src.core import utilities

class TestUtilities(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for testing file I/O
        self.temp_dir = 'temp_test_data'
        os.makedirs(self.temp_dir, exist_ok=True)
        self.test_file_path = os.path.join(self.temp_dir, 'test_file.txt')
        self.test_json_path = os.path.join(self.temp_dir, 'test_data.json')
        self.test_yaml_path = os.path.join(self.temp_dir, 'test_data.yaml')
        
    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # --- File I/O Tests (read_text_file / write_text_file) ---

    def test_write_and_read_text_file(self):
        """Tests that content written can be read back accurately."""
        test_content = "Hello, Scion Agent!"
        utilities.write_text_file(self.test_file_path, test_content)
        read_content = utilities.read_text_file(self.test_file_path)
        self.assertEqual(read_content, test_content)
        
    def test_read_nonexistent_file_with_default(self):
        """Tests reading a non-existent file returns the default content."""
        default = "default content"
        # FIX: Changed load_file_content to read_text_file
        content = utilities.read_text_file(self.test_file_path, default_content=default)
        self.assertEqual(content, default)

    def test_read_nonexistent_file_without_default(self):
        """Tests reading a non-existent file raises FileNotFoundError."""
        # FIX: Changed load_file_content to read_text_file and ensured it raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            utilities.read_text_file(self.test_file_path)
    
    # --- JSON I/O Tests ---

    def test_json_dump_and_load(self):
        """Tests that a dictionary can be saved and loaded as JSON."""
        test_data = {'key': 'value', 'number': 123}
        utilities.json_dump(test_data, self.test_json_path)
        loaded_data = utilities.json_load(self.test_json_path)
        self.assertEqual(loaded_data, test_data)

    def test_json_load_nonexistent_file(self):
        """Tests loading a non-existent JSON file returns an empty dictionary."""
        loaded_data = utilities.json_load("nonexistent.json")
        self.assertEqual(loaded_data, {})
        
    def test_json_load_malformed_file(self):
        """Tests loading a malformed JSON file returns an empty dictionary."""
        with open(self.test_json_path, 'w') as f:
            f.write("{'key': 'value'") # Malformed JSON
        loaded_data = utilities.json_load(self.test_json_path)
        self.assertEqual(loaded_data, {})

    # --- YAML I/O Tests ---

    def test_yaml_safe_dump_and_load(self):
        """Tests that data can be saved and loaded as YAML safely."""
        test_data = {'list': [1, 2, 'a'], 'bool': True}
        utilities.yaml_safe_dump(test_data, self.test_yaml_path)
        loaded_data = utilities.yaml_safe_load(self.test_yaml_path)
        self.assertEqual(loaded_data, test_data)

    def test_yaml_load_nonexistent_file(self):
        """Tests loading a non-existent YAML file returns an empty dictionary."""
        loaded_data = utilities.yaml_safe_load("nonexistent.yaml")
        self.assertEqual(loaded_data, {})

    # --- Other Utility Tests ---

    def test_sanitize_filename_cleans_path(self):
        """Tests that file paths are cleaned of directory traversal components."""
        unsafe_path = "../../../etc/passwd"
        safe_path = "etcpasswd"
        self.assertEqual(utilities.sanitize_filename(unsafe_path), safe_path)
        
        # Test paths with slashes
        complex_path = "src/core/../config.yaml"
        # Since it only cleans directory components, it just removes slashes and dots
        self.assertEqual(utilities.sanitize_filename(complex_path), "srccoreconfigyaml")