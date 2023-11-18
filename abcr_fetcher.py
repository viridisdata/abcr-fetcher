import datetime as dt
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


def get_excel_file_link_metadata(client: httpx.Client) -> dict[str, str]:
    html_page_url = "https://melhoresrodovias.org.br/indice-abcr/"
    r = client.get(html_page_url)
    soup = BeautifulSoup(r.text, "html.parser")
    url = next(
        filter(
            lambda a: a.text.strip() == "Baixe o histórico do Índice",
            soup.select("a"),
        ),
    )["href"]
    filename = url.rsplit("/", maxsplit=1)[1]
    extension = filename.rsplit(".", maxsplit=1)[1]
    r = client.head(url)
    size = int(r.headers["Content-Length"])
    last_modified = dt.datetime.strptime(
        r.headers["Last-Modified"],
        "%a, %d %b %Y %H:%M:%S %Z",
    )
    return {
        "url": url,
        "filename": filename,
        "extension": extension,
        "size": size,
        "last_modified": last_modified,
    }


def fetch_file(
    link_metadata: dict[str, str],
    client: httpx.Client,
    dest_filepath: Path,
):
    dest_filepath.parent.mkdir(parents=True, exist_ok=True)
    url = link_metadata["url"]
    with client.stream("GET", url) as r:
        size = int(r.headers.get("Content-Length", 0))
        size_str = f"{size/1000000: >5.2f}"
        with dest_filepath.open("wb") as f:
            n = 0
            for chunk in r.iter_bytes():
                f.write(chunk)
                n += len(chunk)
                sys.stdout.write(
                    f"Downloading file {dest_filepath.name} "
                    f"{n/1000000: >5.2f} MB of {size_str} MB\r"
                )
                sys.stdout.flush()
    sys.stdout.write("\n")
    sys.stdout.flush()


def get_filename(link_metadata: dict) -> str:
    last_modified = link_metadata["last_modified"]
    extension = link_metadata["extension"]
    filename = f"abcr_{last_modified:%Y%m%d}.{extension}"
    return filename


def fetch(dest_dir: Path):
    client = httpx.Client(timeout=120)
    metadata = get_excel_file_link_metadata(client)
    url = metadata["url"]
    filename = get_filename(metadata)
    dest_filepath = dest_dir / filename
    if dest_filepath.exists():
        return
    fetch_file(url, client, dest_filepath=dest_filepath)


def _cli():
    def get_args():
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-o", "--output", type=Path, default=Path("data"))
        return parser.parse_args()

    args = get_args()
    fetch(dest_dir=args.output)


if __name__ == "__main__":
    _cli()
