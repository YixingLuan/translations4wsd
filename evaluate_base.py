#!/usr/bin/env python
#-*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import sys
import argparse
import subprocess


def get_base_output(system_name, test_name):

    f_path = "base_outputs/ALL." + system_name + ".ranked.out"

    with codecs.open(f_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = {}
    for line in lines:
        line = line.rstrip("\n")
        full_i_id = line.split("\t")[0]
        test_id = full_i_id.split(".")[0]
        i_id = ".".join(full_i_id.split(".")[1:])

        if test_name == "ALL":
            ranked_sense_scores = line.split("\t")[1:]
            prediction = ranked_sense_scores[0].split(" ")[0]
            out[full_i_id] = prediction

        if test_name != "ALL" and test_id == test_name:
            ranked_sense_scores = line.split("\t")[1:]
            prediction = ranked_sense_scores[0].split(" ")[0]
            out[i_id] = prediction

    return out


def run_scorer(test_name):

    key_file = "gold_keys/" + test_name + ".gold.key.txt"

    #cmd1 = "javac Scorer.java"
    #subprocess.run(cmd1, shell=True)
    cmd2 = "java Scorer " + key_file + " tmp.out"

    out1 = subprocess.check_output(cmd2)
    out2 = out1.decode()

    print(out2.rstrip("\r\n"))


def main():

    parser = argparse.ArgumentParser(description='Evaluate the base WSD system.')

    parser.add_argument("-s", "--system", default="", help="name of the base WSD system (babelfy_plain, babelfy_full, ukb_plain, ukb_full, ims, lmms)")
    parser.add_argument("-t", "--test", default="", help="name of test data set (senseval2, senseval3, semeval2007, semeval2013, semeval2015, ALL)") 

    args = parser.parse_args() 

    out = get_base_output(args.system, args.test)

    newf = codecs.open("tmp.out", "w", encoding="utf-8")
    for i_id, sense in out.items():
        line = i_id + " " + sense + "\n"
        newf.write(line)

    newf.close()

    run_scorer(args.test)

    rm_cmd = "rm -f tmp.out"
    subprocess.run(rm_cmd, shell=True)


if __name__ == "__main__":
    main()