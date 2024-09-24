import os
import json

def Realm5_format_data_for_plot(file_path, variable_names):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        data = json.load(f)
    formatted_data = {}
    for variable in variable_names:
        formatted_data[variable] = []
    for time in data:
        for variable in variable_names:
            formatted_data[variable].append(data[time][variable])
    with open("tmp/Realm5_formatted_data.json", "w") as f:
        json.dump(formatted_data, f)

    return "tmp/Realm5_formatted_data.json"

def Realm5_generate_file_url(date_str):
    return f"Realm5/weather_data_{date_str}.json"