import json
from pathlib import Path

DATA_PATH = Path('data/plant_profile.json')

def load_data():
    try:
        with DATA_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'plant_data': []}
    except json.JSONDecodeError:
        print('Error: Failed to decode JSON from the file.')
        return {'plant_data': []}


def save_data(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return data


def get_active_plant(data):
    plant_list = data.get('plant_data', [])
    for plant in plant_list:
        if plant.get('active') == 'active':
            return plant
    return plant_list[0] if plant_list else None


def read():
    data = load_data()
    active_plant = get_active_plant(data)
    if not active_plant:
        print('No plant data available.')
        return
    return active_plant


def update_file(data):
    if not isinstance(data, dict):
        raise ValueError('data must be a dict')

    return save_data(data)


def update_plant(plant_name, species=None, last_watered=None, moisture_percentage=None, make_active=False):
    data = load_data()
    plant_list = data.setdefault('plant_data', [])

    plant = next((p for p in plant_list if p.get('plant_name') == plant_name), None)
    if plant is None:
        plant = {'plant_name': plant_name}
        plant_list.append(plant)
    # TO DO: only update the field that has new info
    if species is not None:
        plant['species'] = species
    if last_watered is not None:
        plant['last_watered'] = last_watered
    if moisture_percentage is not None:
        plant['moisture_percentage'] = moisture_percentage
    if make_active:
        for other in plant_list:
            other['active'] = 'active' if other is plant else 'inactive'

    save_data(data)
    print('Updated plant =', plant)
    return data

def load_examples():
    ns = {}
    with open("data/system_prompts.json") as f:
        exec(f.read(), ns)
    return ns.get("examples", [])