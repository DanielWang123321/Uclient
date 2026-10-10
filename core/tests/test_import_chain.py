"""R1 guard: the sidecar import chain must never pull torch or genesis (design doc §9)."""

import subprocess
import sys


def test_no_torch_or_genesis():
    code = (
        "import sys, uclient_core.rpc, uclient_core.server; from uclient_core.backend import factory;"
        "factory.catalog().info('uf850');"
        "bad=[m for m in sys.modules if m.split('.')[0] in ('torch','genesis')]; print(bad); sys.exit(1 if bad else 0)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
