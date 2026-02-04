import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ENDPOINTS = {
    'stats': '/api/v1/dev-graph/stats',
    'analytics': '/api/v1/dev-graph/analytics',
    'quality': '/api/v1/dev-graph/quality',
    'data_quality': '/api/v1/dev-graph/data-quality/overview',
    'sprints': '/api/v1/dev-graph/sprints',
}


def fetch_json(base_url: str, path: str) -> dict:
    url = base_url.rstrip('/') + path
    with urlopen(url) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description='Export Dev Graph dashboard data as JSON')
    parser.add_argument('--base-url', default='http://localhost:8080')
    parser.add_argument('--output-dir', default='exports/dev-graph/dashboard')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, path in ENDPOINTS.items():
        try:
            payload = fetch_json(args.base_url, path)
        except URLError as exc:
            print(f'Failed to fetch {name} from {path}: {exc}')
            continue
        output_path = output_dir / f'{name}.json'
        output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print('Saved', output_path)


if __name__ == '__main__':
    main()
