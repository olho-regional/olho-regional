
import json
import csv
"""
data = json.load(open("/distritos_geo_api_prep_array.json", "r"))

print(json.dumps(data, indent=2))
"""
#filtered_data_row_count = len(filtered_data)
#values_incluir = set(row['INCLUIR'] for row in filtered_data)


def open_csv_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def open_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_unique_items_from_json(data, key):
    unique_items = set()
    for item in data:
        value = item.get(key)
        if value:
            unique_items.add(value)
    return unique_items


def filter_data_by_column(data, filter_columns):
    return [{col: row[col] for col in filter_columns} for row in data]


def filter_data_by_field_value(data, field_name, value):
    return [row for row in data if row.get(field_name) == value]

def exclude_data_by_field_value(data, field_name, value):
    return [row for row in data if row[field_name].strip() != value]

def lowercase_set(input_set):
    return set(item.lower() for item in input_set)


csv_file = "../data/jornais/jornais regionais - oficial.csv"
distritos_json_file = "../data/localizacao/distritos_geo_api_test1.json"
filter_columns = ['ID', 'TÍTULO', 'ESTADO', 'SUPORTE', 'DATA DE INSCRIÇÃO', 'CHECK MANUAL', 'RAZAO_EXCLUSAO', 'URL', 'Município', 'NOTAS', 'INCLUIR', 'ÂMBITO', 'CONTEÚDO', 'PERIODICIDADE', 'SITUAÇÃO PP', 'DATA DA SITUAÇÃO']

# Data jornais total
data_jornais = open_csv_file(csv_file)
filtered_data_jornais = filter_data_by_column(data_jornais, filter_columns)
data_to_be_included_jornais_1 = filter_data_by_field_value(filtered_data_jornais, 'INCLUIR', 'TRUE')
data_to_be_included_jornais_2 = exclude_data_by_field_value(data_to_be_included_jornais_1, 'Município', '')

print(f"Total records in data jornais: {len(data_jornais)}")
#print(data_to_be_included_jornais_1[0:20])

print(f"records data_to_be_included_jornais_1: {len(data_to_be_included_jornais_1)}")
print(f"records data_to_be_included_jornais_2: {len(data_to_be_included_jornais_2)}")

print(type(data_to_be_included_jornais_1[0]))

data_to_be_included_jornais = data_to_be_included_jornais_2

# Municipios in data jornais total
values_municipio_jornais = list((row['Município'], row['TÍTULO']) for row in data_to_be_included_jornais)


# Data Localizacao total
distritos_data = open_json_file(distritos_json_file)

# Municipios in data localizacao total
municipios_in_distritos_json = extract_unique_items_from_json(distritos_data, 'municipio')
municipios_in_distritos_json_lower = lowercase_set(municipios_in_distritos_json)
distritos_in_distritos_json = extract_unique_items_from_json(distritos_data, 'distrito')
distritos_in_distritos_json_lower = lowercase_set(distritos_in_distritos_json)

#print(distritos_in_distritos_json_lower)
#print("########################")
#print(municipios_in_distritos_json_lower)
#print("########################")
#print(values_municipio_jornais)



results_table = []


for municipio, titulo in values_municipio_jornais:
    searchable = [m.strip() for m in municipio.lower().split(",")]
    searchable = [t.split(":")[1].strip() if ":" in t else t for t in searchable]
    #for t in searchable:
    #    if ":" in t:
    #        searchable.replace(t, t.split()[1])
        
    #searchable_2 = [t.split()[1] for t in searchable if ":" in t else t for t in searchable]
    print(f"searchable: {searchable}")
    result_municipios_list = []
    result_distritos_list = []
    error_list = []
    for word in searchable:
        if word in distritos_in_distritos_json_lower:
            result_distritos_list.append(word)
        elif word in municipios_in_distritos_json_lower:
            result_municipios_list.append(word)
        
        else:
            error_list.append(word)

    results_table.append({
        "Municipio jornal": municipio,
        "Titulo jornal": titulo,
        "municipio": result_municipios_list,
        "distrito)": result_distritos_list,
        "Error": error_list
    })

results_yes = [row for row in results_table if not row["Error"]]
results_no = [row for row in results_table if row["Error"]]
print(json.dumps(results_no, indent=2))
print(f"Total unmatched records: {len(results_no)}")

