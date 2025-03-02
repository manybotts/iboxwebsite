import json

def load_db(filename):
    """Loads a database from a JSON file"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return []

def save_db(filename, data):
    """Saves data to a JSON file"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
