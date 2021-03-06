import os, logging
logging.basicConfig(loglevel=logging.INFO)
from os.path import isfile, splitext, join
from annotateOffs import *
from collections import defaultdict

logging.basicConfig(loglevel=logging.INFO)

from scipy.stats import linregress, pearsonr, spearmanr, mannwhitneyu, rankdata

import matplotlib
matplotlib.use('Agg')
#matplotlib.rcParams['pdf.fonttype'] = 42
import matplotlib.pyplot as plt
import numpy as np

# normalize all scores and KO activity values to percent-rank ?
NORMALIZE = False

scoreCorrFh = None

# the last two score types are not written to the tab-sep file
scoreTypes = ["wangOrig", "doench", "ssc", "chariRaw", "wuCrispr", "crisprScan", "drsc", "fusi", "finalGc6", "finalGg"]

scoreDescs = {
    "wang" : "Wang Score2",
    "wangOrig" : "Wang Score",
    "doench" : "Doench Score",
    "ssc" : "Xu Score",
    "chariRaw" : "Chari Score",
    "chariRank" : "Chari Rank Score",
    "chariRaw" : "Chari Score",
    "finalGc6" : "Ren: last 6 bp GC>4",
    #"finalGc2" : "Farboud-like, last 2 bp GC",
    "finalGg" : "Farboud: ends with GG",
    "myScore" : "Max Score",
    "crisprScan" : "Moreno-Matos Score",
    "fusi" : "Fusi/Doench Score",
    "drsc" : "Housden Score",
    "wuCrispr" : "Wong Score",
    "oof"      : "Bae Out-of-Frame Score"
}

# labels for the different score types
scoreLabels = {
        "wang" : "SVM score2 from Wang et al. 2014",
        "wangOrig" : "SVM score from Wang et al. 2014",
        "doench" : "Regr Score from Doench et al. 2014",
        "chariRank" : "SVM Rank Score Rank from Chari et al. 2015",
        "chariRaw" : "SVM Score from Chari et al. 2015",
        "ssc" : "Regr Score from Xu et al. 2015",
        "fusi" : "Regr Score from Fusi/Doench et al. 2015",
        "wuCrispr" : "SVM Score from Wong et al. 2015",
        "drsc" : "Score from Housden et al. 2015",
        "crisprScan" : "Regr Score from Moreno-Matos et al. 2015",
        "finalGc6" : "last 6bp GC>4, Ren 2015 +/-0.25",
        "finalGg" : "last 2bp=GG , Farboud 2015 +/-0.25"
        }

def plotScores(ax, scores, guideFreqs, scoreType, annotate, diam, doLegend=False):
    " create scatter plot "
    regrX = []
    regrY = []
    plotX = []
    plotY = []

    for extSeq, (guideName, modFreq) in guideFreqs.iteritems():
        y = modFreq
        x = scores[extSeq][scoreType]

        regrX.append(x)
        regrY.append(y)

        # just for plot: adding jitter for a scoretype with many identical scores
        if scoreType.startswith('final'):
            x -= random.random()*0.25

        plotX.append(x)
        plotY.append(y)

    # do not plot more than 3000 dots, makes PDF very slow to display
    #if len(plotX)>3000:
        #print "Sampling scatter plot points down to 3000 points"
        #allDots = [x, y for x, y in zip(plotX, plotY)]
        #allDots = random.sample(allDots, 3000)
        #plotX, plotY = zip(*allDots)

    ax.scatter(plotX, plotY, alpha=.5, marker="o", s=diam, linewidth=0)

    if scoreType in ["wang", "wangOrig"]:
        ax.set_xlim(0, 1.0)
    elif scoreType in ["doench"]:
        ax.set_xlim(0, 100)
    elif scoreType=="chariRank":
        ax.set_xlim(0, 100.0)

    slope, intercept, r_value, p_value, std_err = linregress(regrX,regrY)
    print "score type %s: Pearson R %f, P %f" % (scoreType, r_value, p_value)
    line = slope*np.asarray(regrX)+intercept
    ax.plot(regrX,line, linestyle='-', color="orange")

    pearR, pearP = pearsonr(regrX, regrY)
    spearR, spearP = spearmanr(rankdata(regrX), rankdata(regrY))
    #mwU, mwP = mannwhitneyu(regrX, regrY)
    #ret = pearR
    ret = spearR

    #ax.annotate(r'Pearson R = %0.3f (p %0.3f)' % (pearR, pearP) + '\n' + r'Spearman $\rho$ = %0.3f (p %0.3f)' % (spearR, spearP) + "\nMann-Whitney U=%d (p=%0.3f)" % (int(mwU), mwP), xy=(0.40,0.08), fontsize=9, xycoords='axes fraction')
    ax.annotate(r'Pearson R = %0.3f (p %0.3f)' % (pearR, pearP) + '\n' + r'Spearman $\rho$ = %0.3f (p %0.3f)' % (spearR, spearP), xy=(0.40,0.06), fontsize=9, xycoords='axes fraction')

    return ret


def extendTabAddScores(extFname, scores, scoreNames, outFname):
    " add columns for efficiency scores and write to extFname "
    #outFname = splitext(extFname)[0]+".scores.tab"
    ofh = None
    for row in iterTsvRows(extFname):
        if ofh==None:
            ofh = open(outFname, "w")
            ofh.write("\t".join(row._fields))
            ofh.write("\t")
            ofh.write("\t".join(scoreNames))
            ofh.write("\n")

        ofh.write("\t".join(row)+"\t")

        rowScores = []
        for name in scoreNames:
            rowScores.append(scores[row.extSeq][name])
        ofh.write("\t".join([str(x) for x in rowScores]))
        ofh.write("\n")
    ofh.close()
    print "wrote data to %s" % ofh.name

def plotDataset(datasetName, ax, title, yLabel="Knock-out efficiency", annotate=False, \
        diam=30, addColLabels=True, ylim=None, yTicks=None):
    global scoreCorrFh

    print ("plotting %s" % datasetName)
    scores, freqs = parseEffScores(datasetName)
    ax[0].set_ylabel(yLabel)

    corrs = []
    for index, scoreType in enumerate(scoreTypes):
        doLegend = (index==0)
        corr = plotScores(ax[index], scores, freqs, scoreType, annotate, diam, doLegend=doLegend)
        #if scoreType not in ["finalGc6", "finalGg"]:
        corrs.append(corr)

    # write to tab sep file for heatmap
    row = [datasetDescs.get(datasetName, datasetName) + (" (%d)" % len(freqs)) ]
    row.extend(["%0.3f" % c for c in corrs])
    if scoreCorrFh is not None:
        scoreCorrFh.write("\t".join(row)+"\n")

    #if datasetName.startswith("doench"):
        #for a in ax:
            #a.set_ylim(0, 1.0)
    #ax[0].set_xlim(0, 1.0)
    #ax[1].set_xlim(0, 1.0)
    #ax[3].set_xlim(0, 100)

    if ylim is not None:
        for axObj in ax:
            axObj.set_ylim(*ylim)

    if addColLabels:
        for i in range(len(scoreTypes)):
            ax[i].set_title(scoreLabels[scoreTypes[i]])

    # put the row desc into the left border
    # http://stackoverflow.com/questions/25812255/row-and-column-headers-in-matplotlibs-subplots
    ax[0].annotate(title, xy=(0, 0.5), xytext=(-ax[0].yaxis.labelpad - 5, 0), \
       xycoords=ax[0].yaxis.label, textcoords='offset points', \
       #textcoords='offset points', \
       size='medium', ha='right', va='top')

    if yTicks:
        ax[0].set_yticks(yTicks)

def plotLargeScale(corrFname):
    # large-scale studies to train the scoring models, used for the heat map
    global scoreCorrFh
    scoreCorrFh = open(corrFname, "w")
    scoreCorrFh.write("dataset\t%s\n" % "\t".join([scoreDescs[st] for st in scoreTypes]))

    plotFname = "out/compEffScores-train.pdf"

    rowCount = 25
    fig, axArr = plt.subplots(rowCount, len(scoreTypes))
    axArr = list(axArr)
    fig.set_size_inches(len(scoreTypes)*5,rowCount*5)

    plotDataset("xu2015TrainHl60", axArr.pop(0), "Wang 2014\nhuman HL-60\nProcessed by Xu 2015", diam=2, addColLabels=True, yLabel="-log2 sgRNA fold change")
    plotDataset("xu2015TrainMEsc1", axArr.pop(0), "Wang 2014\nmice mEsc rep 1\nProcessed by Xu 2015", diam=2, addColLabels=True, yLabel="-log2 sgRNA fold change")
    plotDataset("doench2014-Hs", axArr.pop(0), "Doench 2014\nhuman MOLM13, NB4, TF1", diam=2, yLabel="rank-percent", ylim=(0,1.0))
    plotDataset("doench2014-Mm", axArr.pop(0), "Doench 2014\nmouse EL4", diam=2, yLabel="rank-percent", ylim=(0,1.0))
    plotDataset("chari2015Train293T", axArr.pop(0), "Chari 2015\nhuman 293T", diam=2, yLabel="Mutation Rate", ylim=(0,2.0))
    plotDataset("chari2015TrainK562", axArr.pop(0), "Chari 2015\nhuman K562", diam=2, yLabel="Mutation Rate")
    plotDataset("wang2015_hg19", axArr.pop(0), "Wang 2015 Human", diam=1, yLabel="Log-Fold Change")
    plotDataset("doench2016azd_hg19", axArr.pop(0), "Doench 2016\nA375-ETP", diam=1, yLabel="log-fold change")
    #plotDataset("doench20166tg_hg19", axArr.pop(0), "Doench 2016\nA375-6TG", diam=1, yLabel="log-fold change")
    plotDataset("doench2016plx_hg19", axArr.pop(0), "Doench 2016\nA375-PLX", diam=1, yLabel="log-fold change")
    plotDataset("hart2016-Rpe1Avg", axArr.pop(0), "Hart 2016\nRpe1", diam=2, yLabel="avg. log fold change")
    plotDataset("hart2016-Hct1161lib1Avg", axArr.pop(0), "Hart 2016\nHct116, lib 1, rep 1", diam=2, yLabel="avg. log fold change over all time points")
    plotDataset("hart2016-Hct1162lib1Avg", axArr.pop(0), "Hart 2016\nHct116, lib 1, rep 2", diam=2, yLabel="avg. log fold change over all time points")

    plotDataset("morenoMateos2015", axArr.pop(0), "Moreno-Mateos 2015\nZebrafish RNA injection", diam=3)
    plotDataset("varshney2015", axArr.pop(0), "Varshney 2015\nZebrafish RNA injection")
    plotDataset("gagnon2014", axArr.pop(0), "Gagnon 2014\nZebrafish RNA injection")
    plotDataset("liu2016_mm9", axArr.pop(0), "Liu 2016\nMouse Neuro2A, surveyor in-vitro", yLabel="1/0 = effective or not")
    plotDataset("ren2015", axArr.pop(0),  "Ren 2015\nDrosophila injection")
    plotDataset("housden2015", axArr.pop(0),  "Housden 2015\nDrosophila S2R+ cells\nLuciferase-assay")
    plotDataset("farboud2015", axArr.pop(0),  "Farboud 2015\nC. elegans injection")
    plotDataset("ghandi2016_ci2", axArr.pop(0), "Ghandi 2016\nCiona electroporation", yLabel="mutated percent")
    #plotDataset("concordet2-Hs", axArr.pop(0),  "Concordet-Lab\nU2OS, T7 endonucl., gel", yLabel="% modified")
    #plotDataset("concordet2-Mm", axArr.pop(0), "Concordet-Lab\nMEF, T7 endonucl., gel", yLabel="% modified")
    plotDataset("concordet2", axArr.pop(0), "Concordet-Lab\nMEF, U2OS, C6\nT7 Endonucl.", yLabel="% modified")
    plotDataset("schoenig", axArr.pop(0),  "Schoenig\nK562\nLipofection (K2), bGal assay\nbGal: Wefers, PNAS 2013", yLabel="relative rank: 3 (best), 2 or 1", yTicks=[1,2,3])
    plotDataset("alenaAll", axArr.pop(0),  "Shkumatava Lab\nZebrafish\nInjection", yLabel="Mod. frequency from < 20 sequenced clones", ylim=(0,100))
    plotDataset("eschstruth", axArr.pop(0),  "Eschstruth\nZebrafish\nInjection", yLabel="relative rank: 3 (best), 2 or 1", yTicks=[1,2,3])
    plotDataset("teboulVivo_mm9", axArr.pop(0),  "Teboul/Mianne Mouse in vivo singles", yLabel="% of embryos with mutation")

    i = 5
    global datasetDescs
    #for dataset in ["doench2014-Hs-MOLM13_CD15","doench2014-Hs-NB4_CD13","doench2014-Hs-TF1_CD13", "doench2014-Hs-MOLM13_CD33","doench2014-Hs-NB4_CD33","doench2014-Hs-TF1_CD33"]:
    #for dataset in ["doench2014-Hs-MOLM13_CD15","doench2014-Hs-NB4_CD13","doench2014-Hs-TF1_CD13"]:
        #datasetDescs[dataset] = dataset
        #cellType = dataset.split("-")[-1].replace("_", " ")
        #plotDataset(dataset, axArr[i], "hg19", "Doench 2015\nhuman %s" % cellType, diam=2, yLabel="Fold Abundance")
        #i += 1

    fig.tight_layout()
    fig.subplots_adjust(left=0.15, top=0.95)
    fig.savefig(plotFname, format = 'pdf')
    fig.savefig(plotFname.replace(".pdf", ".png"))
    print "wrote plot to %s, added .png" % plotFname
    plt.close()

def plotSmallScale():
    # plot small-scale studies

    figCount = 28
    fig, axArr = plt.subplots(figCount, len(scoreTypes), sharey="row")
    axArr = list(axArr)
    fig.set_size_inches(len(scoreTypes)*5,figCount*4)

    plotFname = "out/compEffScores-valid.pdf"

    plotDataset("xu2015TrainHl60", axArr.pop(0), "Wang 2014\nhuman HL-60\nAs used by Xu 2015", diam=2, addColLabels=True, yLabel="-log2 sgRNA fold change")
    #plotDataset("xu2015TrainKbm7", axArr[1], "Wang 2014\nhuman KBM7\nAs used by Xu 2015", diam=2, addColLabels=True, yLabel="-log2 sgRNA fold change")
    plotDataset("doench2014-Hs", axArr.pop(0), "Doench 2014\nhuman MOLM13, NB4, TF1", diam=2, yLabel="rank-percent", ylim=(0,1.0))
    plotDataset("doench2014-Mm", axArr.pop(0), "Doench 2014\nmouse EL4", diam=2, yLabel="rank-percent", ylim=(0,1.0))
    plotDataset("chari2015Train293T", axArr.pop(0), "Chari 2015\nhuman 293T", diam=2, yLabel="Mutation Rate", ylim=(0,2.0))
    plotDataset("chari2015TrainK562", axArr.pop(0), "Chari 2015\nhuman K562", diam=2, yLabel="Mutation Rate")

    plotDataset("xu2015FOX-AR", axArr.pop(0), "Xu 2015 validation\nLNCaP-abl cells, FOX/AR locus\nLentivirus, Western Blot", addColLabels=True)
    plotDataset("xu2015AAVS1",  axArr.pop(0), "Xu 2015 validation\nLNCaP-abl cells, AAVS1 locus\nLentivirus, T7", addColLabels=True)
    axStart = 5
    #chariCells = ["293T", "A549", "HepG2", "K562", "PGP1iPS", "SKNAS", "U2OS"]
    chariCells = [("293T", "Transfection (Lipofect.)"), ("HepG2", "Transfection (Lonza 4D.)")]
    for i in range(0, len(chariCells)):
        cell, transfDesc = chariCells[i]
        dataset = "chari2015Valid_"+cell
        datasetDescs[dataset] = "Chari 2015 %s Validation" % cell
        plotDataset(dataset, axArr.pop(0), "Chari 2015\nhuman, %s\n%s, sequencing"%(cell, transfDesc))

    plotDataset("doench2014-CD33Exon2", axArr.pop(0), "Doench\nNB4 cells, CDS33 Exon2\nLentivirus", yLabel="sgRNA fold enrichment")
    #plotDataset("doench2014-CD33Exon3", axArr.pop(0), "hg19", "Doench\nNB4 cells\nCD33 Exon3", yLabel="sgRNA fold enrichment")
    #plotDataset("doench2014-CD13Exon10", axArr.pop(0), "hg19", "Doench\nNB4 cells\nCD13 Exon10", yLabel="sgRNA fold enrichment")
    plotDataset("morenoMateos2015", axArr.pop(0), "Moreno-Mateos 2015\nZebrafish RNA injection", diam=3)
    #plotDataset("varshney2015mutF0", axArr.pop(0), "Varshney 2015\nZebrafish RNA injection")
    plotDataset("varshney2015", axArr.pop(0), "Varshney 2015\nZebrafish RNA injection")
    #plotDataset("varshney2015mutF1", axArr.pop(0), "Varshney 2015\nZebrafish RNA injection")
    plotDataset("gagnon2014", axArr.pop(0), "Gagnon 2014\nZebrafish RNA injection")
    plotDataset("liu2016_mm9", axArr.pop(0), "Liu 2016\nMouse Neuro2A, surveyor in-vitro", yLabel="1/0 = effective or not")
    #plotDataset("concordet2-Hs", axArr.pop(0),  "Concordet-Lab\nU2OS, T7 endonucl., gel", yLabel="% modified")
    #plotDataset("concordet2-Mm", axArr.pop(0), "Concordet-Lab\nMEF, T7 endonucl., gel", yLabel="% modified")
    plotDataset("ren2015", axArr.pop(0),  "Ren 2015\nDrosophila injection")
    plotDataset("housden2015", axArr.pop(0),  "Housden 2015\nDrosophila S2R+ cells\nLuciferase-assay")
    plotDataset("farboud2015", axArr.pop(0),  "Farboud 2015\nC. elegans injection")
    plotDataset("ghandi2016_ci2", axArr.pop(0), "Ghandi 2016\nCiona electroporation", yLabel="mutated percent")

    #plotDataset("museumT7", axArr.pop(0),  "Concordet\ncell type?, PPP1R12C locus\nelectrop., T7")
    #plotDataset("museumIC50", axArr.pop(0),  "Concordet\ncells?\nelectrop., IC50 assay(name?)")
    plotDataset("schoenig", axArr.pop(0),  "Schoenig\nK562\nLipofection (K2), bGal assay\nbGal: Wefers, PNAS 2013", yLabel="relative rank: 3 (best), 2 or 1", yTicks=[1,2,3])
    plotDataset("alenaAll", axArr.pop(0),  "Shkumatava Lab\nZebrafish\nInjection", yLabel="Mod. frequency from < 20 sequenced clones", ylim=(0,100))
    #plotDataset("alenaOthers", axArr.pop(0),  "Shkumatava Lab Others\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaPerrine", axArr.pop(0),  "Shkumatava Lab Perreine\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaHelene", axArr.pop(0),  "Shkumatava Lab Helene\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaYuvia", axArr.pop(0),  "Shkumatava Lab Yuvia\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaAntoine", axArr.pop(0),  "Shkumatava Lab Antoine\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaAngelo", axArr.pop(0),  "Shkumatava Lab Angelo", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("alenaHAP", axArr.pop(0),  "Shkumatava: Henele/Antoine/Perrine\nZebrafish\nInjection", yLabel="Mod. frequency", ylim=(0,100))
    plotDataset("eschstruth", axArr.pop(0),  "Eschstruth\nZebrafish\nInjection", yLabel="relative rank: 3 (best), 2 or 1", yTicks=[1,2,3])
    #plotDataset("teboulVitro_mm9", axArr.pop(0),  "Teboul/Mianne Mouse In-vitro singles", yLabel="% modified")
    plotDataset("teboulVivo_mm9", axArr.pop(0),  "Teboul/Mianne Mouse in vivo singles", yLabel="% of embryos with mutation")
    #plotDataset("concordet2-Rn", axArr.pop(0), "rn5", "")
    #plotDataset("concordet2", axArr.pop(0),  "Concordet\nhuman/mouse/rat, cellType?\nDelivery?", yLabel="relative rank: 3(best), 2 or 1")

    global datasetDescs

    fig.tight_layout()
    fig.subplots_adjust(left=0.15, top=0.95)
    fig.savefig(plotFname, format = 'pdf')
    fig.savefig(plotFname.replace(".pdf", ".png"))
    print "wrote plot to %s, added .png" % plotFname
    plt.close()

    if scoreCorrFh is not None:
        print "wrote score R summary to %s" % scoreCorrFh.name

def main():
    #"XuData/modFreq.tab" 
    #extendTabAddContext("temp.tab")

    plotLargeScale("out/effScoreComp.tsv")
    plotSmallScale()
    scoreCorrFh.close()

main()
