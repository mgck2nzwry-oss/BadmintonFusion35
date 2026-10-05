"""Explicit opt-in for legacy scripts that write into a local project copy."""
from pathlib import Path
import json
import os

if os.environ.get('BADMINTON_LEGACY_ALLOW_WRITE') != 'YES':
    raise RuntimeError('Legacy scripts may overwrite derived files. Use a separate project COPY and set BADMINTON_LEGACY_ALLOW_WRITE=YES after reading legacy_reference/README.md.')
value = os.environ.get('BADMINTON_LEGACY_ROOT')
if not value:
    raise RuntimeError('Set BADMINTON_LEGACY_ROOT to the copied project directory; no local default is used.')
LEGACY_ROOT = Path(value).resolve(strict=True)
if not LEGACY_ROOT.is_dir() or LEGACY_ROOT == Path(LEGACY_ROOT.anchor):
    raise ValueError('Expected a specific existing project directory, not a drive root.')


def load_windows(key):
    """Read authorized session-specific display windows; none are bundled."""
    path = os.environ.get('BADMINTON_LEGACY_WINDOWS')
    if not path:
        raise RuntimeError('Set BADMINTON_LEGACY_WINDOWS to your session-window JSON. See legacy_reference/README.md.')
    values = json.loads(Path(path).read_text(encoding='utf-8'))[key]
    if len(values) != 10 or any(len(v) != 2 or not float(v[0]) < float(v[1]) for v in values):
        raise ValueError('Expected ten [start, end] display windows, each start < end.')
    return values
