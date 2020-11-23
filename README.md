# Improving Word Sense Disambiguation with Translations

This repository contains the source code to replicate the results on our EMNLP2020 paper [Improving Word Sense Disambiguation with Translations](https://www.aclweb.org/anthology/2020.emnlp-main.332/).

We include our replication scripts/results for base WSD systems and our methods. 
Also, please find the presented word alignment algorithm BabAlign [here](https://github.com/YixingLuan/BabAlign).


## Table of Contents

- [Tested Environment](#requirement)
- [Tools and Data](#tools-and-data)
- [Replication](#replication)
- [Our Methods](#our-methods)
- [References](#references)


## Tested Environment

- Python: 3.6.8
- Java: OpenJDK 1.8.0_201


## Tools and Data

- [WSD Unified Framework](http://lcl.uniroma1.it/wsdeval/) - All of our results (including replications) are based on test data from this framework
(To perform following experiments, please download this [evaluation framework](http://lcl.uniroma1.it/wsdeval/) and place `Scorer.java` under this directory. Then, please compile it by running `javac Scorer.java`.)
- [Babelfy (Moro et al., 2014)](http://babelfy.org/) - Used as a base knowledge-based WSD system
- [UKB (Agirre et al., 2014, 2018)](https://ixa2.si.ehu.es/ukb/) - Used as a base knowledge-based WSD system
- [IMS (Zhong and Ng, 2010)](https://www.comp.nus.edu.sg/~nlp/software.html) - Used as a base supervised WSD system
- [LMMS (Loureiro and Jorge, 2019)](https://github.com/danlou/LMMS) - Used as a base supervised WSD system
- [OneSeC (Scarlini et al., 2019)](http://www.trainomatic.org/) - Automatic multilingual corpora used to train IMS for multilingual WSD 
- [SensEmBERT (Scarlini et al., 2020)](http://sensembert.org/) - Used as a base knowledge-based multilingual WSD system
- [CluBERT (Pasini et al., 2020)](https://github.com/SapienzaNLP/clubert) - Used as p_freq in our SoftConstraint method for multilingual WSD


## Replication

We get the following replication results of above systems:

| System | | SE2 | SE3 | SE07 | SE13 | SE15 | ALL |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Babelfy (full) | reported | 67.0 | 63.5 | 51.6 | 66.4 | 70.3 | 65.5 |
|                | ours     | 66.6 | 65.5 | 53.0 | 63.0 | 68.5 | 64.9 |
| UKB (full)     | reported | 68.8 | 66.1 | 53.0 | 68.8 | 70.3 | 67.3 |
|                | ours     | 68.8 | 66.1 | 53.0 | 68.8 | 70.3 | 67.3 |
| IMS            | reported | 70.9 | 69.3 | 61.3 | 65.3 | 69.5 | 68.4 |
|                | ours     | 71.3 | 69.1 | 61.5 | 65.1 | 68.3 | 68.3 |
| LMMS           | reported | 76.3 | 75.6 | 68.1 | 75.1 | 77.0 | 75.4 |
|                | ours     | 76.3 | 75.4 | 67.9 | 75.0 | 76.9 | 75.3 |

| System | | SE13 DE | SE13 ES | SE13 FR | SE13 IT | SE15 ES | SE15 IT |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| IMS (OneSeC) | ours | 72.5 | 67.8 | 69.4 | 68.0 | 62.4 | 64.7 |
| SensEmBERT | reported | 78.0 | 74.6 | 78.0 | 69.6 | 64.1 | 66.0 |
|            | ours | 77.3 | 74.8 | 78.5 | 70.4 | 64.7 | 67.7 |


### [evaluate_base.py](https://github.com/YixingLuan/translations4wsd/blob/master/evaluate_base.py) - Test replication results of the base WSD systems on English all-words WSD

Sense predictions (senses ranked by probabilities) from all base systems are ready under [`base_outputs`](https://github.com/YixingLuan/translations4wsd/blob/master/base_outputs).

Usage description:

```
$ python3 evaluate_base.py -h
usage: evaluate_base.py [-h] [-s SYSTEM] [-t TEST]

Evaluate the base WSD system.

optional arguments:
  -h, --help                    show this help message and exit
  -s SYSTEM, --system SYSTEM    name of the base WSD system (babelfy_plain, babelfy_full, ukb_plain, ukb_full, ims, lmms)
  -t TEST, --test TEST          name of test data set (senseval2, senseval3, semeval2007, semeval2013, semeval2015, ALL)
```

This show precision / recall / F1 based on the official scoring script (`Scorer.java`).


### [evaluate_base_mwsd.py](https://github.com/YixingLuan/translations4wsd/blob/master/evaluate_base_mwsd.py) - Test replication results of the base WSD systems on Multilingual WSD

Sense predictions (senses ranked by probabilities) from all base systems for all test languages are ready under [`mwsd_base_outputs`](https://github.com/YixingLuan/translations4wsd/blob/master/mwsd_base_outputs).

Usage description:

```
$ python3 evaluate_base_mwsd.py -h
usage: evaluate_base_mwsd.py [-h] [-s SYSTEM] [-t TEST] [-l LANG]
                             [--type TYPE]

Evaluate the base Multilingual WSD system.

optional arguments:
  -h, --help                    show this help message and exit
  -s SYSTEM, --system SYSTEM    name of the base MWSD system (ims, sensembert)
  -t TEST, --test TEST          name of test data set (semeval2013, semeval2015)
  -l LANG, --lang LANG          test language (de, es, fr, it (de and fr are only for semeval2013))
  --type TYPE                   type of the test file (dev, tst, all)
```

This show precision / recall / F1 based on the official scoring script (`Scorer.java`).


## Our Methods

You can replicate our reported results with our HardConstraint, SoftConstraint, and t_emb methods. 
Our results include the following improvements for knowledge-based systems:

| System | Method | SE2 | SE3 | SE07 | SE13 | SE15 | ALL |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| UKB (full) | base | 68.8 | 66.1 | 53.0 | 68.8 | 70.3 | 67.3 |
|            | Hard | 68.5 | 65.5 | 53.6 | 64.5 | 69.7 | 66.1 |
|            | Soft | 71.3 | 66.8 | 54.1 | 69.0 | 74.2 | 68.9 |

| System | Method | SE13 DE | SE13 ES | SE13 FR | SE13 IT | SE15 ES | SE15 IT |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| SensEmBERT | base | 76.7 | 74.7 | 77.6 | 70.7 | 64.4 | 68.7 |
|            | Hard | 77.1 | 80.1 | 79.3 | 76.6 | 63.5 | 72.8 |
|            | Soft | 76.8 | 81.9 | 80.8 | 78.3 | 64.6 | 73.6 |
|            | Soft + CluBERT | 76.8 | 79.2 | 81.5 | 79.8 | 66.4 | 78.7 |
|            | Soft + t_emb + CluBERT | 79.6 | 81.4 | 81.5 | 78.9 | 66.6 | 78.7 |


### [translations4wsd.py](https://github.com/YixingLuan/translations4wsd/blob/master/translations4wsd.py) - Test our methods with various base WSD systems on English all-words WSD

It uses sense-translation mappings produced based on translations from NMT models and BabelNet. 
All sense-translation mappings are available under [`mappings`](https://github.com/YixingLuan/translations4wsd/blob/master/mappings).

Usage description:

```
$ python3 translations4wsd.py -h
usage: translations4wsd.py [-h] [-s SYSTEM] [-t TEST] [-m METHOD] [-o OUT]

Test and evaluate translations for WSD methods (English all-words WSD)

optional arguments:
  -h, --help                    show this help message and exit
  -s SYSTEM, --system SYSTEM    name of the base WSD system (babelfy_plain, babelfy_full, ukb_plain, ukb_full, ims, lmms)
  -t TEST, --test TEST          name of test data set (senseval2, senseval3, semeval2007, semeval2013, semeval2015, ALL)
  -m METHOD, --method METHOD    name of the method (hard or soft)
  -o OUT, --out OUT             name of the output file
```

This will produce an output file under [`outputs`](https://github.com/YixingLuan/translations4wsd/blob/master/outputs).
Also, this will show precision / recall / F1 based on the official scoring script (`Scorer.java`).


### [translations4wsd_mwsd.py](https://github.com/YixingLuan/translations4wsd/blob/master/translations4wsd_mwsd.py) - Test our methods with various base WSD systems on multilingual WSD

It uses sense-translation mappings produced based on translations from test data and BabelNet. 
All sense-translation mappings are available under [`mwsd_mappings`](https://github.com/YixingLuan/translations4wsd/blob/master/mwsd_mappings).

If you would like to test our SoftConstraint method with [CluBERT](https://github.com/SapienzaNLP/clubert), please download it and place the `clubert_v1.0` folder under this directory. 
If you change the folder name or file names for CluBERT, please adjust paths in `line 558`.

Usage description:

```
$ python3 translations4wsd_mwsd.py -h
usage: translations4wsd_mwsd.py [-h] [-s SYSTEM] [-t TEST] [-l LANG]
                                [--type TYPE] [-m METHOD] [--clubert] [--temb]
                                [-o OUT]

Test and evaluate translations for WSD methods (Multilingual WSD)

optional arguments:
  -h, --help                    show this help message and exit
  -s SYSTEM, --system SYSTEM    name of the base WSD system (ims, sensembert)
  -t TEST, --test TEST          name of test data set (semeval2013, semeval2015)
  -l LANG, --lang LANG          test language (de, es, fr, it)
  --type TYPE                   type of the test file (dev, tst, all)
  -m METHOD, --method METHOD    name of the method (hard or soft)
  --clubert                     flag to enable CluBERT sense frequency distributions (default: False)
  --temb                        flag to enable t_emb method (only for SensEmBERT, default: False)
  -o OUT, --out OUT             name of the output file
```

This will produce an output file under [`mwsd_outputs`](https://github.com/YixingLuan/translations4wsd/blob/master/mwsd_outputs).
Also, this will show precision / recall / F1 based on the official scoring script (`Scorer.java`).


## References

```
@inproceedings{luan-etal-2020-improving,
    title = "Improving Word Sense Disambiguation with Translations",
    author = "Luan, Yixing  and
      Hauer, Bradley  and
      Mou, Lili  and
      Kondrak, Grzegorz",
    booktitle = "Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)",
    month = nov,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.emnlp-main.332",
    pages = "4055--4065",
}
```
