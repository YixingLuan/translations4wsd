#!/usr/bin/env python
#-*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import sys
import argparse
import subprocess


def get_base_output(system_name, test_name, lang, t_type):

    if t_type == "all":
        f_path = "mwsd_base_outputs/" + test_name + "." + lang.lower() + "." + system_name + ".ranked.dev.out" # add dev instances first
    else:
        f_path = "mwsd_base_outputs/" + test_name + "." + lang.lower() + "." + system_name + ".ranked." + t_type + ".out"

    with codecs.open(f_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = {}
    for line in lines:
        line = line.rstrip("\n")
        i_id = line.split("\t")[0]
        ranked_sense_scores = line.split("\t")[1:]
        prediction = ranked_sense_scores[0].split(" ")[0]
        out[i_id] = prediction

    if t_type == "all": 
        f_path = "mwsd_base_outputs/" + test_name + "." + lang + "." + system_name + ".ranked.tst.out" # add remaining instances
        
        with codecs.open(f_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.rstrip("\n")
            i_id = line.split("\t")[0]
            ranked_sense_scores = line.split("\t")[1:]
            prediction = ranked_sense_scores[0].split(" ")[0]
            out[i_id] = prediction


    return out


def run_scorer(test_name, lang, t_type):

    if t_type == "all":
        key_file = "mwsd_gold_keys/" + test_name + "_" + lang.lower() + ".gold.key.txt"
    else:
        key_file = "mwsd_gold_keys/" + test_name + "_" + lang.lower() + ".gold." + t_type + ".key"

    #cmd1 = "javac Scorer.java"
    #subprocess.run(cmd1, shell=True)
    cmd2 = "java Scorer " + key_file + " tmp.out"

    out1 = subprocess.check_output(cmd2)
    out2 = out1.decode()

    print(out2.rstrip("\r\n"))


def main():

    parser = argparse.ArgumentParser(description='Evaluate the base Multilingual WSD system.')

    parser.add_argument("-s", "--system", default="", help="name of the base MWSD system (ims, sensembert)")
    parser.add_argument("-t", "--test", default="", help="name of test data set (semeval2013, semeval2015)") 
    parser.add_argument("-l", "--lang", default="", help="test language (de, es, fr, it)")
    parser.add_argument("--type", default="", help="type of the test file (dev, tst, all)")

    args = parser.parse_args() 

    out = get_base_output(args.system, args.test, args.lang, args.type)

    newf = codecs.open("tmp.out", "w", encoding="utf-8")
    for i_id, sense in out.items():
        line = i_id + " " + sense + "\n"
        newf.write(line)

    newf.close()

    run_scorer(args.test, args.lang, args.type)

    rm_cmd = "rm -f tmp.out"
    subprocess.run(rm_cmd, shell=True)


if __name__ == "__main__":
    main()