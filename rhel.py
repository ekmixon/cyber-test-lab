#!/usr/bin/env python

import json
import os
import sys
import traceback

from datetime import datetime

sys.path.append('.')
from cybertestlab import CyberTestLab

__author__ = 'Jason Callaway'
__email__ = 'jasoncallaway@fedoraproject.org'
__license__ = 'GNU Public License v2'
__version__ = '0.3'
__status__ = 'beta'


def main(argv):
    debug = True
    now = datetime.now()
    output_dir = sys.argv[1]
    repo_dir = sys.argv[2]
    swap_path = sys.argv[3]
    repos = ['.']
    ctl = CyberTestLab.CyberTestLab(repo_dir=repo_dir,
                                    swap_path=swap_path,
                                    repo_list=repos,
                                    debug=True)
    ctl.redteam.funcs.mkdir_p(repo_dir)
    ctl.redteam.funcs.mkdir_p(swap_path)

    # if debug:
    #     print('+ syncing repos')
    # ctl.repo_sync('reposync')

    for repo in ctl.repo_list:
        if debug:
            print(f'+ {repo}')
        for root, dirs, files in os.walk(f'{repo_dir}/{repo}'):
            for filename in files:
                if debug:
                    print(f'+ {filename}')
                results_dir = f'{output_dir}/{filename[0]}'
                results_file = f'{results_dir}/{filename}.json'
                if not os.path.isfile(results_file):
                    if debug:
                        print(f'++ analyzing {filename}')
                    ctl.prep_swap()
                    try:
                        analyze(ctl, repo, filename, results_dir, results_file)
                    except Exception as e:
                        print(f'analysis failed on {filename}')
                        traceback.print_exc()
                        continue


def analyze(ctl, repo, filename, results_dir, results_file):
    ctl.prep_rpm(repo, filename)
    metadata = ctl.get_metadata(filename)
    if elfs := ctl.find_elfs():
        results = ctl.scan_elfs(filename, elfs)
        ctl.redteam.funcs.mkdir_p(results_dir)
        with open(results_file, 'w') as f:
            json.dump({'metadata': metadata,
                       'results': results}, f, indent=4)
    else:
        with open(results_file, 'w') as f:
            json.dump({'metadata': metadata,
                       'results': 'no elfs found'}, f, indent=4)


if __name__ == "__main__":
    main(sys.argv)
