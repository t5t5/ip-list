#!/usr/bin/env python3
# generate_lists__iplist_json.py

import json
import urllib.request
import urllib.error
import os
import sys
import argparse
from pathlib import Path

BASE_URL = "https://iplist.opencck.org/?format=json&site={service}&filesave=1"

def fetch_json(url):
    """Скачивает JSON с указанного URL"""
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"ERROR: Failed to fetch URL: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return None

def generate_list_name(service):
    """
    Генерирует имя списка из service.
    
    Примеры:
    lostfilm.tv -> lostfilm_addrlist
    telegram.org -> telegram_addrlist
    youtube.com -> youtube_addrlist
    xxx.yyy.zzz -> xxx_addrlist
    """
    name_part = service.split('.')[0]
    return f"{name_part}_addrlist"

def generate_rsc(service, entries, list_name, output_file):
    """
    Генерирует .rsc файл для MikroTik
    """
    if not entries:
        print(f"WARNING: No entries for {service}, file not created")
        return False
    
    # Сортируем записи для стабильного вывода
    sorted_entries = sorted(entries)
    
    lines = [
        f"# Auto-generated for {service}",
        f"# List: {list_name}",
        f"/ip firewall address-list remove [find list=\"{list_name}\"];",
        ":delay 5s",
        "",
        "/ip firewall address-list"
    ]
    
    for entry in sorted_entries:
        lines.append(f"add list={list_name} address={entry} comment={service}")
    
    # Добавляем пустую строку в конце файла
    lines.append("")
    
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Generated {len(sorted_entries)} entries -> {output_file}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to write file: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Generate MikroTik address list from iplist.opencck.org"
    )
    
    parser.add_argument(
        "--service",
        required=True,
        help="Service name (e.g., lostfilm.tv)"
    )
    
    parser.add_argument(
        "--type",
        required=True,
        choices=["ip4", "cidr4", "domains"],
        help="Type of data to extract (ip4, cidr4, domains)"
    )
    
    parser.add_argument(
        "--out",
        required=True,
        help="Output .rsc file path"
    )
    
    parser.add_argument(
        "--list",
        required=False,
        help="List name in MikroTik (default: auto-generated from service)"
    )
    
    args = parser.parse_args()
    
    # Определяем имя списка
    list_name = args.list if args.list else generate_list_name(args.service)
    
    # Формируем URL
    url = BASE_URL.format(service=args.service)
    print(f"Fetching: {url}")
    
    # Скачиваем JSON
    data = fetch_json(url)
    if data is None:
        sys.exit(0)
    
    # Проверяем, что data - это словарь
    if not isinstance(data, dict):
        print(f"ERROR: Unexpected response format (not a dictionary)", file=sys.stderr)
        sys.exit(0)
    
    # Проверяем наличие сервиса
    if args.service not in data:
        print(f"ERROR: Service '{args.service}' not found in JSON", file=sys.stderr)
        if isinstance(data, dict):
            print(f"Available: {', '.join(data.keys())}", file=sys.stderr)
        sys.exit(0)
    
    service_data = data[args.service]
    
    # Проверяем наличие поля type
    if args.type not in service_data:
        print(f"ERROR: Field '{args.type}' not found for service '{args.service}'", file=sys.stderr)
        print(f"Available fields: {', '.join(service_data.keys())}", file=sys.stderr)
        sys.exit(0)
    
    entries = service_data[args.type]
    
    if not isinstance(entries, list):
        print(f"ERROR: Field '{args.type}' is not a list", file=sys.stderr)
        sys.exit(0)
    
    if entries:
        generate_rsc(args.service, entries, list_name, args.out)
    else:
        print(f"WARNING: No entries for {args.service}.{args.type}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
