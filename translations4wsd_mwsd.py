#!/usr/bin/env python
#-*- coding: utf-8 -*-

import codecs
from collections import defaultdict
import subprocess
import sys
import argparse
import glob

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

def get_p_freq(file_path, id_lemma_map):

    # p_freq

    with codecs.open(file_path, "r", encoding="utf-8") as f:
        sense_info = f.readlines()

    tmp_sense_freq_dict = defaultdict(dict)
    for s_i in sense_info:
        s_i = s_i.rstrip("\n")
        lemma_pos = s_i.split("\t")[0].replace("#", " ")
        sense_prob_list = s_i.split("\t")[1:]
        for sense_prob in sense_prob_list:
            if "#" not in sense_prob:
                sense = sense_prob
                prob = float(1.0)
            else:
                sense = sense_prob.split("#")[0]
                prob = sense_prob.split("#")[1]
            tmp_sense_freq_dict[lemma_pos][sense] = float(prob)

    sense_freq_dict = {}
    for i_id, lemma_pos in id_lemma_map.items():
        sense_prob_dict = tmp_sense_freq_dict[lemma_pos]
        sense_freq_dict[i_id] = sense_prob_dict


    return sense_freq_dict


def load_id_lemma_map(file_path):    

    with codecs.open(file_path, "r", encoding="utf-8") as f:
        lemma_lines = f.readlines()

    id_lemma_map = {}
    for lemma_l in lemma_lines:
        lemma_l = lemma_l.rstrip("\n")
        i_id = lemma_l.split("\t")[0]
        lemma_pos = lemma_l.split("\t")[1]
        id_lemma_map[i_id] = lemma_pos

    return id_lemma_map


def load_trans_sense_constraint(test_name, file_path):    

    with codecs.open(file_path, "r", encoding="utf-8") as f:
        t_s_map = f.readlines()

    t_s_constraint = {}
    for t_s_l in t_s_map:
        t_s_l = t_s_l.rstrip("\n")
        t_s_info_list = t_s_l.split("\t")
        i_id = t_s_info_list[0] 
        target_lemma_pos = t_s_info_list[1]

        if len(t_s_info_list) != 4: # no sense trans mapping or sense trans mapping for babel senses only (don't exist in wordnet)
            t_s_constraint[i_id] = target_lemma_pos

        elif len(t_s_info_list) == 4: # valid sense trans mapping
            aligned_trans = t_s_info_list[2]
            if aligned_trans == "MONOSEMOUS":
                t_s_constraint[i_id] = target_lemma_pos

            else:
                bn_syn_candidates = t_s_info_list[3].split(" ")
                t_s_constraint[i_id] = [target_lemma_pos, bn_syn_candidates]

    return t_s_constraint


def get_intersect2(t_s_constraint1, t_s_constraint2):

    # HardConstraint (intersection among 2 languages)

    t_s_constraint_intersect = {}

    for i_id, info1 in t_s_constraint1.items():
        if type(info1) == str:
            target_lemma_pos = info1
        else:
            target_lemma_pos = info1[0]

        info2 = t_s_constraint2[i_id]     

        if type(info1) == list and type(info2) == list:
            intersection = list(set(info1[1]).intersection(set(info2[1])))
            if intersection == []:
                t_s_constraint_intersect[i_id] = target_lemma_pos
            else:
                t_s_constraint_intersect[i_id] = [target_lemma_pos, intersection]
        
        else:
            t_s_constraint_intersect[i_id] = target_lemma_pos

    return t_s_constraint_intersect


def get_intersect4(t_s_constraint1, t_s_constraint2, t_s_constraint3, t_s_constraint4):

    # HardConstraint (intersection among 4 languages)

    t_s_constraint_intersect = {}

    for i_id, info1 in t_s_constraint1.items():
        if type(info1) == str:
            target_lemma_pos = info1
        else:
            target_lemma_pos = info1[0]
        info2 = t_s_constraint2[i_id]
        info3 = t_s_constraint3[i_id]
        info4 = t_s_constraint4[i_id]

        if type(info1) == list and type(info2) == list and type(info3) == list and type(info4) == list:
            intersection = list(set(info1[1]).intersection(set(info2[1]), set(info3[1]), set(info4[1])))
            if intersection == []:
                t_s_constraint_intersect[i_id] = target_lemma_pos
            else:
                t_s_constraint_intersect[i_id] = [target_lemma_pos, intersection]
        
        else:
            t_s_constraint_intersect[i_id] = target_lemma_pos

    return t_s_constraint_intersect


def get_p_trans(ranked_sense_scores, trans_constraint_candidates1, trans_constraint_candidates2, trans_constraint_candidates3, trans_constraint_candidates4, smoothing):

    # p_trans with 2 or 4 languages

    # get sum for normalization first
    all_sum = 0.0
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        if sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4)
        
        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3)
        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates4)
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4)

        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2)
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3)
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates4)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates4)
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4)

        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates1)
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates2)
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates3)
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            all_sum += 1/len(trans_constraint_candidates4)       

    if all_sum == 0.0:
        constraint_scores = {}
        for sense_score in ranked_sense_scores:
            sense = sense_score[0]
            constraint_scores[sense] = 1
        return constraint_scores    

    # preparing scores from constraint
    constraint_scores = {}
    for sense_score in ranked_sense_scores:
        sense = sense_score[0]
        if sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

        elif sense in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates2) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates2) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates3) + 1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

        elif sense in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates1) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates2) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense in trans_constraint_candidates3 and sense not in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates3) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score
        elif sense not in trans_constraint_candidates1 and sense not in trans_constraint_candidates2 and sense not in trans_constraint_candidates3 and sense in trans_constraint_candidates4:
            cons_score = float(1/len(trans_constraint_candidates4) + smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

        else:
            cons_score = float(smoothing) / ((len(ranked_sense_scores) * smoothing)  + all_sum)
            constraint_scores[sense] = cons_score

    return constraint_scores


def get_p_wsd(system_name, test_name, lang, t_type):

    if t_type == "all":
        f_path = "mwsd_base_outputs/" + test_name + "." + lang.lower() + "." + system_name + ".ranked.dev.out" # add dev instances first
    else:
        f_path = "mwsd_base_outputs/" + test_name + "." + lang.lower() + "." + system_name + ".ranked." + t_type + ".out"

    with codecs.open(f_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    base = {}
    for line in lines:
        line = line.rstrip("\n")
        i_id = line.split("\t")[0]
        ranked_sense_scores = line.split("\t")[1:]
        base[i_id] = [pair.split(" ") for pair in ranked_sense_scores]

    if t_type == "all": 
        f_path = "mwsd_base_outputs/" + test_name + "." + lang + "." + system_name + ".ranked.tst.out" # add remaining instances
        
        with codecs.open(f_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.rstrip("\n")
            i_id = line.split("\t")[0]
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


def HardConstraint(test_name, t_type, lang, out_name, base, t_s_constraint_intersect):

    out_path = "mwsd_outputs/" + out_name
    newf = codecs.open(out_path, "w", encoding="utf-8")

    for i_id, ranked_sense_scores in base.items():

        ans_sense = ranked_sense_scores[0][0]

        if len(ranked_sense_scores) == 1 or i_id not in t_s_constraint_intersect: 
            # monosemous words
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

    evaluate_wsd(test_name, t_type, lang, out_path)


def SoftConstraint(test_name, t_type, lang, out_name, base, sense_freq_dict, t_s_constraint1, t_s_constraint2, t_s_constraint3, t_s_constraint4, a, b, c, smoothing):

    out_path = "mwsd_outputs/" + out_name
    newf = codecs.open(out_path, "w", encoding="utf-8")

    for i_id, p_wsd in base.items():

        ans_sense = p_wsd[0][0]

        if len(p_wsd) == 1: 
            # monosemous words
            line = i_id + " " + ans_sense + "\n"
            newf.write(line)
            continue

        try:
            if type(t_s_constraint1[i_id]) == str:
                remain_sense_candidates1 = []
            elif type(t_s_constraint1[i_id]) == list:
                remain_sense_candidates1 = t_s_constraint1[i_id][1]
        except:
            remain_sense_candidates1 = []
        try:
            if type(t_s_constraint2[i_id]) == str:
                remain_sense_candidates2 = []
            elif type(t_s_constraint2[i_id]) == list:
                remain_sense_candidates2 = t_s_constraint2[i_id][1]
        except:
            remain_sense_candidates2 = []
        try:
            if type(t_s_constraint3[i_id]) == str:
                remain_sense_candidates3 = []
            elif type(t_s_constraint3[i_id]) == list:
                remain_sense_candidates3 = t_s_constraint3[i_id][1]
        except:
            remain_sense_candidates3 = []
        try:
            if type(t_s_constraint4[i_id]) == str:
                remain_sense_candidates4 = []
            elif type(t_s_constraint4[i_id]) == list:
                remain_sense_candidates4 = t_s_constraint4[i_id][1]
        except:
            remain_sense_candidates4 = []
        
        if remain_sense_candidates1 == [] and remain_sense_candidates2 == [] and remain_sense_candidates3 == [] and remain_sense_candidates4 == []:
            ans_sense_with_trans = ans_sense
        else:
            p_trans = get_p_trans(p_wsd, remain_sense_candidates1, remain_sense_candidates2, remain_sense_candidates3, remain_sense_candidates4, smoothing)
            if c: # use p_freq
                p_freq = sense_freq_dict[i_id]
                ranked_sense_scores = combine_all_experts(p_wsd, p_trans, p_freq, a, b, c)
            else:
                ranked_sense_scores = combine_all_experts_plain(p_wsd, p_trans, a, b)
            ans_sense_with_trans = ranked_sense_scores[0][0]

        tst_line = i_id + " " + ans_sense_with_trans + "\n"
        newf.write(tst_line)

    newf.close()

    evaluate_wsd(test_name, t_type, lang, out_path)


def evaluate_wsd(test_name, t_type, lang, out_path):

    if t_type == "all":
        key_file = "mwsd_gold_keys/" + test_name + "_" + lang.lower() + ".gold.key.txt"
    else:
        key_file = "mwsd_gold_keys/" + test_name + "_" + lang.lower() + ".gold." + t_type + ".key"

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

    parser = argparse.ArgumentParser(description="Test and evaluate translations for WSD methods (Multilingual WSD)")

    parser.add_argument("-s", "--system", default="", help="name of the base WSD system (ims, sensembert)")
    parser.add_argument("-t", "--test", default="", help="name of test data set (semeval2013, semeval2015)") 
    parser.add_argument("-l", "--lang", default="", help="test language (de, es, fr, it)")
    parser.add_argument("--type", default="", help="type of the test file (dev, tst, all)")
    parser.add_argument("-m", "--method", default="", help="name of the method (hard or soft)")
    parser.add_argument("--clubert", default=False, action="store_true", help="flag to enable CluBERT sense frequency distributions (default: False)")
    parser.add_argument("--temb", default=False, action="store_true", help="flag to enable t_emb method (only for SensEmBERT, default: False)")
    parser.add_argument("-o", "--out", default="", help="name of the output file")
    
    args = parser.parse_args()

    parameters = {"ims": {"semeval2013 DE": {"t_smoothing": 0.01, "a": 0.9, "b": 0.1, "c": None}, 
                          "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                          "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.5, "b": 0.5, "c": None},
                          "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                          "semeval2015 ES": {"t_smoothing": 0.56, "a": 0.3, "b": 0.7, "c": None},
                          "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None}
                         },
                  "ims.clubert": {"semeval2013 DE": {"t_smoothing": 0.01, "a": 0.1, "b": 0.3, "c": 0.6},
                                  "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.1, "b": 0.5, "c": 0.4},
                                  "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.5, "b": 0.4, "c": 0.1},
                                  "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.8, "c": 0.1},
                                  "semeval2015 ES": {"t_smoothing": 0.01, "a": 0.2, "b": 0.3, "c": 0.5},
                                  "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.8, "c": 0.1}
                                 },
                  "sensembert": {"semeval2013 DE": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                 "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                 "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                 "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                 "semeval2015 ES": {"t_smoothing": 0.01, "a": 0.9, "b": 0.1, "c": None},
                                 "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None}
                                },
                  "sensembert.temb": {"semeval2013 DE": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                      "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                      "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                      "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None},
                                      "semeval2015 ES": {"t_smoothing": 0.01, "a": 0.9, "b": 0.1, "c": None},
                                      "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.9, "c": None}
                                     },
                  "sensembert.clubert": {"semeval2013 DE": {"t_smoothing": 0.00, "a": 0.8, "b": 0.1, "c": 0.1},
                                         "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.8, "b": 0.1, "c": 0.1},
                                         "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.1, "b": 0.7, "c": 0.2},
                                         "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.3, "c": 0.6},
                                         "semeval2015 ES": {"t_smoothing": 0.03, "a": 0.6, "b": 0.1, "c": 0.3},
                                         "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.1, "c": 0.8}
                                        },
                  "sensembert.temb.clubert": {"semeval2013 DE": {"t_smoothing": 0.00, "a": 0.1, "b": 0.1, "c": 0.8},
                                              "semeval2013 ES": {"t_smoothing": 0.00, "a": 0.1, "b": 0.2, "c": 0.7},
                                              "semeval2013 FR": {"t_smoothing": 0.00, "a": 0.1, "b": 0.7, "c": 0.2},
                                              "semeval2013 IT": {"t_smoothing": 0.00, "a": 0.4, "b": 0.5, "c": 0.1},
                                              "semeval2015 ES": {"t_smoothing": 0.02, "a": 0.7, "b": 0.1, "c": 0.2},
                                              "semeval2015 IT": {"t_smoothing": 0.00, "a": 0.1, "b": 0.1, "c": 0.8}
                                             }
                 }

    system_name = args.system
    test_name = args.test
    lang = args.lang
    t_type = args.type

    if args.temb: 
        if system_name != "sensembert":
            print("t_emb is only for sensembert!")
            sys.exit()
        system_name = system_name + ".temb"

    base = get_p_wsd(system_name, test_name, lang, t_type)

    tmp_path = "mwsd_mappings/" + test_name + "_bnsyn_trans_mapping.*." + lang + ".txt"
    mapping_path_list = glob.glob(tmp_path)

    if len(mapping_path_list) == 4: # semeval2013
        t_s_constraint1 = load_trans_sense_constraint(test_name, mapping_path_list[0])
        t_s_constraint2 = load_trans_sense_constraint(test_name, mapping_path_list[1])
        t_s_constraint3 = load_trans_sense_constraint(test_name, mapping_path_list[2])
        t_s_constraint4 = load_trans_sense_constraint(test_name, mapping_path_list[3])
    elif len(mapping_path_list) == 2: # semeval2015
        t_s_constraint1 = load_trans_sense_constraint(test_name, mapping_path_list[0])
        t_s_constraint2 = load_trans_sense_constraint(test_name, mapping_path_list[1])
        t_s_constraint3 = None
        t_s_constraint4 = None

    id_lemma_path = "mwsd_mappings/" + test_name + "_" + lang + "_lemma_bnsyn_mapping.txt"
    id_lemma_map = load_id_lemma_map(id_lemma_path)

    if args.method == "hard":
        if test_name == "semeval2013":
            t_s_constraint_intersect = get_intersect4(t_s_constraint1, t_s_constraint2, t_s_constraint3, t_s_constraint4)
        elif test_name == "semeval2015":
            t_s_constraint_intersect = get_intersect2(t_s_constraint1, t_s_constraint2)
        HardConstraint(test_name, t_type, lang, args.out, base, t_s_constraint_intersect)

    elif args.method == "soft":
        if args.clubert:
            system_name = system_name + ".clubert"
            file_path = "clubert_v1.0/" + lang + "/lexemes_distributions.bnid.txt"
            sense_freq_dict = get_p_freq(file_path, id_lemma_map)
        else:
            sense_freq_dict = None
        test_case = test_name + " " + lang.upper()
        a, b, c, t_smoothing = parameters[system_name][test_case]["a"], parameters[system_name][test_case]["b"], parameters[system_name][test_case]["c"], parameters[system_name][test_case]["t_smoothing"]
        SoftConstraint(test_name, t_type, lang, args.out, base, sense_freq_dict, t_s_constraint1, t_s_constraint2, t_s_constraint3, t_s_constraint4, a, b, c, t_smoothing)
        

if __name__ == "__main__":
    main()