import json
from pathlib import Path
import subprocess
import shlex
import os
import re

# Replace curly-brace surrounded variables with
# the corresponding value in 'values'
# Example: insert_named_valued('Hello {name}', {'name': 'Bob'})
# -> 'Hello Bob'
def insert_named_values(string, values):
    return re.sub(r'{([a-zA-Z0-9_]+)}', lambda m: values[m.group(1)], string)

def parse_json_file(file_path):
    with open(file_path, 'r') as probe_config_file:
        probe_file_contents = probe_config_file.read()

    return json.loads(probe_file_contents)

# Easy way to recursively iterate over all json files in a directory
# Usage: for parsed_json in all_json_in_dir(path):
def all_json_in_dir(dir_path):
    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(dir_path).glob('**/*.json')
    for path in pathlist:
        parsed = parse_json_file(str(path))
        yield parsed

def load_modules():
    modules = {}

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
    for config in all_json_in_dir(path):
        for key, value in config.items():
            if key in modules:
                # Module of same type was already defined somewhere else
                raise ValueError('Duplicate module')

            modules[key] = value

    return modules

modules = load_modules()

def run_module(module_type, config, bound_values):
    module = modules[module_type]

    populated_config = {k: insert_named_values(v, bound_values) for k, v in config.items()}
    quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}

    populated_command = insert_named_values(module['command'], quoted_config)

    script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = script.communicate()

    output = output.decode('utf-8')
    error = error.decode('utf-8')

    if error != '':
        print(error)
        return False
    else:
        print(output)
        return output

def handle_config(config, current_commit_dir, previous_commit_dir):
    bound_values = {}

    for module in config:
        output = run_module(module['type'], module['config'], bound_values)
        if 'name' in module:
            bound_values[module['name']] = output

def iterate_over_configs(current_commit_dir, previous_commit_dir):
    path = os.path.join(current_commit_dir, 'monitoring')
    for config in all_json_in_dir(path):
        handle_config(config, current_commit_dir, previous_commit_dir)

iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))