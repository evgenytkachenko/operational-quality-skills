import argparse
import json
import os
from pathlib import Path
from .core import Config, analyze
from .inquiry import handoff, local_assessment, validate_assessment


def read_json(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(1000001)
    if len(raw) > 1000000:
        raise ValueError('input exceeds one MB')
    return json.loads(raw)


def save(directory, name, value):
    path = directory / name
    # Never overwrite an existing investigation; files are private to the local user.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description='Read-only operational investigation')
    parser.add_argument('--config', required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--mock', help='Synthetic fixture JSON; never calls a service')
    inputs.add_argument('--live-read', action='store_true', help='Explicitly enable configured read-only services')
    parser.add_argument('--output', required=True, help='New output directory')
    model = parser.add_mutually_exclusive_group()
    model.add_argument('--local-model', help='Explicit installed Ollama model; no download')
    model.add_argument('--assessment', help='Host-agent JSON draft to validate against this retrieval')
    args = parser.parse_args()
    try:
        config = Config.model_validate(read_json(args.config))
        if args.mock:
            fixture = read_json(args.mock)
            def fetch(source, cfg):
                value = fixture[source.name]
                if 'error' in value:
                    raise RuntimeError('synthetic unavailable source')
                return value['rows'], value.get('limitations', [])
        else:
            from .integrations import fetch_live
            fetch = fetch_live
        directory = Path(args.output)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        packet = analyze(config, fetch)
        save(directory, 'evidence.json', packet)
        save(directory, 'inquiry.json', handoff(packet))
        if args.local_model:
            report = local_assessment(packet, args.local_model)
            save(directory, 'review.json', report)
        elif args.assessment:
            raw = json.dumps(read_json(args.assessment))
            save(directory, 'review.json', validate_assessment(raw, packet))
        print(f'Investigation written to {directory}; human review required.')
    except Exception as exc:
        # Deliberately no vendor/validation payload dumps to terminal.
        parser.exit(2, f'Investigation failed ({type(exc).__name__}). Check configuration, budgets and source access. Existing output may contain a partial packet.\n')


if __name__ == '__main__':
    main()


def review_main():
    parser = argparse.ArgumentParser(description='Validate a host-agent assessment against a saved evidence packet; no service calls')
    parser.add_argument('--packet', required=True)
    parser.add_argument('--assessment', required=True)
    parser.add_argument('--output', required=True, help='New private output directory')
    args = parser.parse_args()
    try:
        packet = read_json(args.packet)
        report = validate_assessment(json.dumps(read_json(args.assessment)), packet)
        directory = Path(args.output)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        save(directory, 'review.json', report)
        print(f'Review draft written to {directory}; semantic support unverified.')
    except Exception as exc:
        parser.exit(2, f'Review rejected ({type(exc).__name__}); check schema, packet integrity and citations.\n')
