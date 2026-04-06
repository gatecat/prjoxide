import json
import os
import re

from bs4 import BeautifulSoup
from pathlib import Path

def normalize_text(s: str) -> str:
    return " ".join(s.encode('ascii', errors='ignore').decode("ascii").replace("(default)", "").split())

def extract_cell_value(td):
    text = normalize_text(td.get_text())
    matches = re.findall(r'"([^"]*)"', text)
    if len(matches):
        return matches

    divs = td.find_all("div", class_="CellBody", recursive=False)
    if not divs:
        return text

    values = [normalize_text(d.get_text()) for d in divs if normalize_text(d.get_text())]
    if len(values) == 0:
        return ""

    if len(values) == 1:
        return values[0]
    return values


def parse_table(table):
    rows = table.find_all("tr")
    if not rows:
        return []

    # Extract headers
    header_cells = rows[0].find_all(["th", "td"])
    headers = [normalize_text(h.get_text()) or f"col_{i}" for i, h in enumerate(header_cells)]

    data = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        row_obj = {}
        for header, cell in zip(headers, cells):
            if header == "col_1":
                header = "Values"
            cell_value = extract_cell_value(cell)
            if header == "Values" and not isinstance(cell_value, list):
                cell_value = [cell_value]
            row_obj[header] = cell_value



        if row_obj.get("Name", None) == "":
            if "Values" not in data[-1]:
                data[-1]["Values"] = []

            data[-1]["Values"].extend(row_obj.get("Values", []))
            #data[-1]["Description"] += (row_obj.get("Description", ""))
        else:
            data.append(row_obj)

    return data


def scrape_html(html_path: Path, out_dir = "./primitives"):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    title = soup.title.get_text(strip=True) if soup.title else html_path.stem
    output = {}

    output["description"] = "".join([div.get_text() for div in soup.select(".BodyAfterHead")])
    output["platforms"] = [ supported_platforms.get_text() for supported_platforms in soup.select(".Bulleted")]

    for title_div in soup.select("div.TableTitle"):
        table_title = normalize_text(title_div.get_text())
        if not table_title:
            continue

        table = title_div.find_parent("table")
        if not table:
            continue

        output[table_title] = parse_table(table)

    output_path = Path(out_dir) / Path(f"{title.replace('/', '_')}.json")
    print(output_path, out_dir, title)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python scrape.py <file.html>")
        sys.exit(1)

    html_file = Path(sys.argv[1])
    out = scrape_html(html_file)
    print(f"Wrote {out}")
