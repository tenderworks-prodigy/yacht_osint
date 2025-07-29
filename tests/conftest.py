import gzip
import logging
import sys
from pathlib import Path

import vcr
from vcr.persisters.filesystem import (
    CassetteNotFoundError,
    FilesystemPersister,
)
from vcr.serialize import deserialize, serialize

logging.getLogger("urllib3.connectionpool").disabled = True

# ensure project root is on the import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class GzipPersister(FilesystemPersister):
    @classmethod
    def load_cassette(cls, cassette_path, serializer):
        cassette_path = Path(cassette_path)
        if not cassette_path.is_file():
            raise CassetteNotFoundError()
        with gzip.open(cassette_path, "rt") as f:
            data = f.read()
        return deserialize(data, serializer)

    @staticmethod
    def save_cassette(cassette_path, cassette_dict, serializer):
        data = serialize(cassette_dict, serializer)
        cassette_path = Path(cassette_path)
        cassette_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(cassette_path, "wt") as f:
            f.write(data)


vcr.default_vcr.register_persister(GzipPersister)
