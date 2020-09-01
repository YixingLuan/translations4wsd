#!/usr/bin/env python
#-*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import subprocess
import sys
import argparse

'''
# HardConstraint

Simply rule-out senses if they are not mapped to the given translation in BabelNet


# SoftConstraint

p(sense) = p_wsd^a * p_trans^b * p_freq^c

p_wsd = score produced by WSD system (normalized)
p_trans = scores based on translations in BabelNet (normalized)
           --> perform additive smoothing to make it as a soft constraint (normalized)
p_freq = prior knowledge about sense frequency distribution 
          --> sense frequency in WordNet (also perform additive smoothing)

a, b, c, smoothing weights are tunable parameter
'''

def get_p_freq(smoothing):

    # p_freq

    with codecs.open("index.sense", "r", encoding="utf-8") as f:
        sense_info = f.readlines()

    sense_count_dict = defaultdict(dict)
    for s_i in sense_info:
        s_i = s_i.rstrip("\n").rstrip("\r")
        sense_key = s_i.split(" ")[0]
        lemma = sense_key.split("%")[0]
        num_pos = sense_key.split("%")[1][0]
        if num_pos == "1":
            pos = "n"
        elif num_pos == "2":
            pos = "v"
        elif num_pos == "3" or num_pos == "5":
            pos = "a" 
        elif num_pos == "4":
            pos = "r" 
        sense_count = int(s_i.split(" ")[-1])
        lemma_pos = lemma + " " + pos
        sense_count_dict[lemma_pos][sense_key] = sense_count + smoothing


    sense_freq_dict = defaultdict(dict)
    for lemma_pos, sense_counts in sense_count_dict.items():
        sum_count = 0
        for sense, count in sense_counts.items():
            sum_count += count
        for sense, count in sense_counts.items():
            sense_freq = float(count) / sum_count
            sense_freq_dict[lemma_pos][sense] = sense_freq

    return sense_freq_dict


def load_trans_sense_constraint(test_name, lang):

    if lang == "FR":
        mapping_name = "mappings/ALL_bnsyn_trans_mapping.wmt14.en-fr.txt"
    elif lang == "DE":
        mapping_name = "mappings/ALL_bnsyn_trans_mapping.wmt16.en-de.txt"
    elif lang == "RU":
        mapping_name = "mappings/ALL_bnsyn_trans_mapping.wmt19.en-ru.txt"
    

    with codecs.open(mapping_name, "r", encoding="utf-8") as f:
        t_s_map = f.readlines()

    t_s_constraint = {}
    for t_s_l in t_s_map:
        t_s_l = t_s_l.rstrip("\n")
        t_s_info_list = t_s_l.split("\t")
        i_id = t_s_info_list[0] 

        if test_name != "ALL":
            if i_id.split(".")[0] != test_name:
                continue
            i_id = ".".join(i_id.split(".")[1:])

        if len(t_s_info_list) != 5: # no sense trans mapping or sense trans mapping for babel senses only (don't exist in wordnet)
            target_lemma_pos = t_s_info_list[1]
            t_s_constraint[i_id] = target_lemma_pos

        elif len(t_s_info_list) == 5: # valid sense trans mapping
            target_lemma_pos = t_s_info_list[1]
            aligned_trans = t_s_info_list[2]
            if aligned_trans == "MONOSEMOUS":
                target_lemma_pos = t_s_info_list[1]
                t_s_constraint[i_id] = target_lemma_pos

            else:
                bn_syn_candidates = t_s_info_list[3].split(" ")
                wn_sense_candidates = t_s_info_list[4].split(" ")
                t_s_constraint[i_id] = [target_lemma_pos, wn_sense_candidates]

    return t_s_constraint


def get_intersect(t_s_constraint1, t_s_constraint2, t_s_constraint3):

    # HardConstraint (intersection among 3 languages)

    t_s_constraint_intersect = {}

    for i_id, info1 in t_s_constraint1.items():
        if type(info1) == str:
            target_lemma_pos = info1
        else:
            target_lemma_pos = info1[0]
        info2 = t_s_constraint2[i_id]
        info3 = t_s_constraint3[i_id]

        if type(info1) == list and type(info2) == list and type(info3) == list:
            intersection = list(set(info1[1]).intersection(set(info2[1]), set(info3[1])))
            if intersection == []:
                t_s_constraint_intersect[i_id] = target_lemma_pos
            else:
                t_s_constraint_intersect[i_id] = [target_lemma_pos, intersection]
        
        else:
            t_s_constraint_intersect[i_id] = target_lemma_pos

    return t_s_constraint_intersect


def get_p_trans(ranked_sense_scores, trans_constraint_candidates1, trans_constraint_candidates2, trans_constraint_candidates3, smoothing):

    # p_trans with 3 languages

    # get sum for normalization first
    all_sum = 0.0
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        if sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3)
        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2)
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3)
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates1)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates2)
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            all_sum += 1/len(trans_constraint_candidates3)

    # preparing scores from constraint
    constraint_scores = {}
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        if sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates1) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates2) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3:
            cons_score = float(1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        else:
            cons_score = float(smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

    return constraint_scores


def get_p_wsd(system_name, test_name):

    f_path = "base_outputs/ALL." + system_name + ".ranked.out"

    with codecs.open(f_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    base = {}
    for line in lines:
        line = line.rstrip("\n")
        full_i_id = line.split("\t")[0]
        test_id = full_i_id.split(".")[0]
        i_id = ".".join(full_i_id.split(".")[1:])

        if test_name == "ALL":
            ranked_sense_scores = line.split("\t")[1:]
            base[full_i_id] = [pair.split(" ") for pair in ranked_sense_scores]

        if test_name != "ALL" and test_id == test_name:
            ranked_sense_scores = line.split("\t")[1:]
            base[i_id] = [pair.split(" ") for pair in ranked_sense_scores]

    return base


def combine_all_experts_plain(ranked_sense_scores, trans_cons_factor, a, b):

    # culculate p(sense) = p(wsd)^a * p(translation)^b 
    new_ranked_sense_scores = []
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        p_wsd = float(sense_score[1])
        p_trans = trans_cons_factor[sense]
        new_score = pow(p_wsd, a) * pow(p_trans, b)
        new_ranked_sense_scores.append([sense, new_score])

    new_ranked_sense_scores.sort(key=lambda x:x[1], reverse=True)

    return new_ranked_sense_scores


def combine_all_experts(ranked_sense_scores, trans_cons_factor, sense_freq, a, b, c):

    # culculate p(sense) = p(wsd)^a * p(translation)^b * p(prior)^c
    new_ranked_sense_scores = []
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        p_wsd = float(sense_score[1])
        p_trans = trans_cons_factor[sense]
        if sense not in sense_freq:
            p_freq = 0
        else:
            p_freq = sense_freq[sense]
        new_score = pow(p_wsd, a) * pow(p_trans, b) * pow(p_freq, c)
        new_ranked_sense_scores.append([sense, new_score])

    new_ranked_sense_scores.sort(key=lambda x:x[1], reverse=True)

    return new_ranked_sense_scores


def HardConstraint(test_name, out_name, base, t_s_constraint_intersect):

    out_path = "outputs/" + out_name
    newf = codecs.open(out_path, "w", encoding="utf-8")

    for i_id, ranked_sense_scores in base.items():

        ans_sense = ranked_sense_scores[0][0]

        if len(ranked_sense_scores) == 1: 
            # predictions from WN1st sense backoff or monosemous words
            line = i_id + " " + ans_sense + "\n"
            newf.write(line)
            continue

        constraint = t_s_constraint_intersect[i_id]
        if type(constraint) == str:
            ans_sense_with_trans = ans_sense

        elif type(constraint) == list:
            remain_sense_candidates = constraint[1]
            if ans_sense in remain_sense_candidates:
                ans_sense_with_trans = ans_sense
            else:
                find_flag = 0
                for pair in ranked_sense_scores[1:]:
                    sense = pair[0]
                    if sense in remain_sense_candidates:
                        ans_sense_with_trans = sense
                        find_flag += 1
                        break
                if find_flag == 0:
                    ans_sense_with_trans = ans_sense

        line = i_id + " " + ans_sense_with_trans + "\n"
        newf.write(line)

    newf.close()

    evaluate_wsd(test_name, out_path)


def SoftConstraint(test_name, out_name, base, sense_freq_dict, t_s_constraint1, t_s_constraint2, t_s_constraint3, a, b, c, smoothing):

    out_path = "outputs/" + out_name
    newf = codecs.open(out_path, "w", encoding="utf-8")

    for i_id, p_wsd in base.items():

        ans_sense = p_wsd[0][0]

        if len(p_wsd) == 1: 
            # predictions from WN1st sense backoff or monosemous words
            line = i_id + " " + ans_sense + "\n"
            newf.write(line)
            continue

        lemma = ans_sense.split("%")[0]
        num_pos = ans_sense.split("%")[1][0]
        if num_pos == "1":
            pos = "n"
        elif num_pos == "2":
            pos = "v"
        elif num_pos == "3" or num_pos == "5":
            pos = "a" 
        elif num_pos == "4":
            pos = "r" 
        lemma_pos = lemma + " " + pos

        if type(t_s_constraint1[i_id]) == str:
            remain_sense_candidates1 = []
        elif type(t_s_constraint1[i_id]) == list:
            remain_sense_candidates1 = t_s_constraint1[i_id][1]
        if type(t_s_constraint2[i_id]) == str:
            remain_sense_candidates2 = []
        elif type(t_s_constraint2[i_id]) == list:
            remain_sense_candidates2 = t_s_constraint2[i_id][1]
        if type(t_s_constraint3[i_id]) == str:
            remain_sense_candidates3 = []
        elif type(t_s_constraint3[i_id]) == list:
            remain_sense_candidates3 = t_s_constraint3[i_id][1]

        if remain_sense_candidates1 == [] and remain_sense_candidates2 == [] and remain_sense_candidates3 == []:
            ans_sense_with_trans = ans_sense
        else:
            p_trans = get_p_trans(p_wsd, remain_sense_candidates1, remain_sense_candidates2, remain_sense_candidates3, smoothing)
            if c: # use p_freq
                p_freq = sense_freq_dict[lemma_pos]
                ranked_sense_scores = combine_all_experts(p_wsd, p_trans, p_freq, a, b, c)
            else:
                ranked_sense_scores = combine_all_experts_plain(p_wsd, p_trans, a, b)
            ans_sense_with_trans = ranked_sense_scores[0][0]

        tst_line = i_id + " " + ans_sense_with_trans + "\n"
        newf.write(tst_line)

    newf.close()

    evaluate_wsd(test_name, out_path)


def evaluate_wsd(test_name, out_path):

    key_file = "gold_keys/" + test_name + ".gold.key.txt"

    cmd = [
        "java", 
        "Scorer", 
        key_file,
        out_path,
        ]

    b_out = subprocess.check_output(cmd)
    s_out = b_out.decode()

    print(s_out.rstrip("\r\n"))


def main():

    parser = argparse.ArgumentParser(description="Test and evaluate translations for WSD methods (English all-words WSD)")

    parser.add_argument("-s", "--system", default="", help="name of the base WSD system (babelfy_plain, babelfy_full, ukb_plain, ukb_full, ims, lmms)")
    parser.add_argument("-t", "--test", default="", help="name of test data set (senseval2, senseval3, semeval2007, semeval2013, semeval2015, ALL)") 
    parser.add_argument("-m", "--method", default="", help="name of the method (hard or soft)")
    parser.add_argument("-o", "--out", default="", help="name of the output file")
    
    args = parser.parse_args()

    parameters = {"babelfy_plain": {"s_smoothing": None, "t_smoothing": 0.01, "a": 0.1, "b": 0.9, "c": None}, 
                  "babelfy_full": {"s_smoothing": 0.01, "t_smoothing": 0.01, "a": 0.1, "b": 0.4, "c": 0.5},
                  "ukb_plain": {"s_smoothing": None, "t_smoothing": 0.01, "a": 0.3, "b": 0.7, "c": None},
                  "ukb_full": {"s_smoothing": 0.02, "t_smoothing": 1.00, "a": 0.1, "b": 0.8, "c": 0.1},
                  "ims": {"s_smoothing": 0.01, "t_smoothing": 0.48, "a": 0.5, "b": 0.4, "c": 0.1},
                  "lmms": {"s_smoothing": 0.01, "t_smoothing": 0.87, "a": 0.8, "b": 0.1, "c": 0.1}
                }

    system_name = args.system
    test_name = args.test

    base = get_p_wsd(system_name, test_name)

    if args.method == "hard":
        t_s_constraint1 = load_trans_sense_constraint(test_name, "FR")
        t_s_constraint2 = load_trans_sense_constraint(test_name, "DE")
        t_s_constraint3 = load_trans_sense_constraint(test_name, "RU")
        t_s_constraint_intersect = get_intersect(t_s_constraint1, t_s_constraint2, t_s_constraint3)
        HardConstraint(test_name, args.out, base, t_s_constraint_intersect)

    elif args.method == "soft":
        t_s_constraint1 = load_trans_sense_constraint(test_name, "FR")
        t_s_constraint2 = load_trans_sense_constraint(test_name, "DE")
        t_s_constraint3 = load_trans_sense_constraint(test_name, "RU")
        if parameters[system_name]["s_smoothing"]:
            sense_freq_dict = get_p_freq(parameters[system_name]["s_smoothing"])
        else:
             sense_freq_dict = None
        a, b, c, t_smoothing = parameters[system_name]["a"], parameters[system_name]["b"], parameters[system_name]["c"], parameters[system_name]["t_smoothing"]
        SoftConstraint(test_name, args.out, base, sense_freq_dict, t_s_constraint1, t_s_constraint2, t_s_constraint3, a, b, c, t_smoothing)
        

if __name__ == "__main__":
    main()