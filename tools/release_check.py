"""Ensure secrets stay out of the versionable source and functional status is healthy."""
import json
import re
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

from host import ROOT, RUN


if __name__ == '__main__':
    credentials = json.loads((RUN / 'credentials.json').read_text())
    files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    leaks = []
    for name in files:
        p = ROOT / name
        if not p.is_file(): continue
        try: content = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError): continue
        if any(value in content for value in credentials.values()) or re.search(r'^-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----$', content, re.M):
            leaks.append(name)
    if leaks: raise RuntimeError('Secret material in versionable files: ' + ', '.join(leaks))
    query = urllib.parse.urlencode({'query': 'naslab_job_last_run_success'})
    values = json.load(urllib.request.urlopen('http://127.0.0.1:9090/api/v1/query?' + query))['data']['result']
    assert len(values) >= 4 and all(row['value'][1] == '1' for row in values)
    assert not any(name.startswith('.runtime/') or name.startswith('.runtime\\') for name in files)
    print(json.dumps({'secret_scan': 'PASS', 'versionable_files': len(files),
        'last_job_results': {row['metric']['job']: row['value'][1] for row in values},
        'runtime_ignored': True}, indent=2))
