import json
import os


def clean_monitoring_data(file_path):
    if not os.path.exists(file_path):
        print(f"Arquivo {file_path} não encontrado.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    original_count = len(data)
    # Mantém apenas onde 'actual' é um número inteiro (ex: 22.0)
    # Entradas incorretas usam médias como 22.454545...
    cleaned_data = [d for d in data if float(d["actual"]).is_integer()]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2)

    print(f"Limpeza concluída: {original_count} -> {len(cleaned_data)} entradas.")


if __name__ == "__main__":
    clean_monitoring_data("model_monitoring.json")
