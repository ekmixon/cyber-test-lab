#!/usr/bin/env python

import os
import json
import yaml

import numpy as np

__author__ = 'Jason Callaway'
__email__ = 'jasoncallaway@fedoraproject.org'
__license__ = 'GNU Public License v2'
__version__ = '0.3'
__status__ = 'beta'


class Scoring(object):
    def __init__(self, debug=False, schema='./scoring.yml'):
        self.debug = debug
        with open(schema, 'r') as f:
            self.score_schema = yaml.load(f)
    
    def score(self, path):
        scores = {}
        for root, dirs, files in os.walk(path):
            for directory in dirs:
                if self.debug:
                    print(f'+ walking {path}/{directory}')
                for r, d, f in os.walk(f'{path}/{directory}'):
                    for filename in f:
                        abspath = f'{path}/{directory}/{filename}'

                        if self.debug:
                            print(f'++ scoring {abspath}')
                        binary_scores = self.score_json(abspath)
                        if binary_scores is None or len(binary_scores.keys()) == 0:
                            continue

                        bscores = [binary_scores[binary] for binary in binary_scores.keys()]
                        package_score = np.mean(bscores)

                        scores[filename] = {"package_score": package_score,
                                            "binary_scores": binary_scores}
        return scores

    def score_json(self, filename):
        try:
            with open(filename, 'r') as f:
                jsondata = json.load(f)
        except Exception as e:
            return None

        if type(jsondata['results']) is unicode:
            return None

        binary_scores = {}
        binaries = jsondata['results'].keys()
        for binary in binaries:
            if self.debug:
                print(f'+++ scoring binary {binary}')
            score = self.score_binary(jsondata['results'][binary])
            if score is None:
                continue
            binary_scores[binary] = score

        return binary_scores

    def score_binary(self, binary_json):
        score = self.score_schema['starting_score']

        hardening = binary_json['hardening-check']
        # quick sanity checks
        if len(hardening.keys()) == 0 or '/bin/sh' in hardening.keys():
            return None
        if binary_json.get('find-libc-functions'):
            libc_functions = set(binary_json['find-libc-functions'])
        else:
            libc_functions = set()
        functions = set(binary_json['report-functions'])
        complexity = binary_json['complexity']['r2aa']
        complexity_schema = self.score_schema['complexity']
        hardening_schema = self.score_schema['hardening-check']

        # handle cyclomatic complexity
        if type(complexity) is not unicode:
            if complexity['afCc'] is not None:
                c = int(complexity['afCc'])
                m = int(complexity_schema['cyclomatic_complexity']['mean'])
                s = int(complexity_schema['cyclomatic_complexity']['stdev'])
                o = int(complexity_schema['cyclomatic_complexity']['stdev_coefficient'])
                a = (c - m) / s
                score += a * o

            # handle cycle cost
            if complexity['afC'] is not None:
                c = int(complexity['afC'])
                m = int(complexity_schema['cycle_cost']['mean'])
                s = int(complexity_schema['cycle_cost']['stdev'])
                o = int(complexity_schema['cycle_cost']['stdev_coefficient'])
                a = (c - m) / s
                score += a * o

        # handle hardening check values
        for check in hardening_schema.keys():
            for value in hardening_schema[check].keys():
                if value in hardening[f' {check}']:
                    score += hardening_schema[check][value]

        # check for bad functions
        bad_functions = set(self.score_schema['bad_functions']['functions'])
        addend = self.score_schema['bad_functions']['addend']
        if bad_functions.union(libc_functions):
            score += addend
        if bad_functions.union(functions):
            score += addend

        return score
