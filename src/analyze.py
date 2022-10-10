import math
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn import metrics
from nltk.metrics import edit_distance
import numpy as np
import nltk
import scipy as sp
from itertools import product
from wordcloud import WordCloud
from scipy.cluster.hierarchy import dendrogram

nltk.download(['swadesh'])

from nltk.corpus import swadesh


"""This module contains functions for analyzing the languages as well as helper functions for plotting"""


def plot_languages(x, y, labels=None, languages=None):

    if labels is not None:
        
        categories = labels.unique()
        markers = ['x', 'o', 'd']
        colors = sns.color_palette("deep", n_colors=7)

        for label, (marker, color) in zip(categories, product(markers, colors)):
            cond = (labels == label)
            plt.scatter(x[cond], y[cond], color=color, marker=marker)


    if languages is not None:
        texts = [plt.text(x[i], y[i], languages[i]) for i in range(len(languages))]

    plt.xlabel('x')
    plt.ylabel('y')

    fig = plt.gcf()

    return fig



def plot_language_groups(labels):

    counts = labels['family'].value_counts()

    ncols = 6
    fig, ax  = plt.subplots(nrows = len(counts)//ncols+1, ncols=ncols, dpi=600)
    
    for j in range(len(counts)%ncols, ncols):
        ax[len(counts)//ncols, j].remove()

    for i, family in enumerate(counts.keys()):
        ax[i//ncols, i%ncols].set_title(family, fontsize=8)

        lang = labels[labels['family']==family]

        wc = WordCloud(width=1000, height=1000, prefer_horizontal=1, collocations=True, background_color='white', 
                        max_font_size=400/np.sqrt(len(lang)), colormap="tab10")
        freq = pd.Series(index=lang['name'].apply(lambda x: x.split(' ')[0] if '(' in x else x), data=np.ones(len(lang))).to_dict()
    
        ax[i//ncols, i%ncols].imshow(wc.fit_words(freq))
        ax[i//ncols, i%ncols].set_axis_off()
        # ax[i//ncols, i%ncols].set_xticks([])
        # ax[i//ncols, i%ncols].set_yticks([])

    fig.tight_layout()
    return fig



def dist_to_word(words, word, transpositions=True):

    word = str(word)
    distances = pd.Series(words, dtype=str).apply(lambda x: edit_distance(x, word, transpositions=transpositions))

    return distances



def score_model(pred_abels, true_labels):

    score_funcs = [
        ('adjusted_rand_score', metrics.adjusted_rand_score),
        ('adjusted_mutual_info_score', metrics.adjusted_mutual_info_score),
        ('homogeneity_score', metrics.homogeneity_score),
        ('completeness_score', metrics.completeness_score),
        ('v_measure_score', metrics.v_measure_score),
        ('fowlkes_mallows_score', metrics.fowlkes_mallows_score)
        ]
    
    scores = {}

    for name, scorer in score_funcs:
        scores[name] = scorer(pred_abels, true_labels)


    return scores



def pairwise_word_distances(data:pd.DataFrame)->pd.Series:
    """Generates pairwise distance for each word

    Args:
        data (pd.DataFrame): DataFrame of transliterations where columns are languages and rows are words

    Returns:
        pd.Series: Pairwise ditance matrix for each word
    """
    
    pw_distances = data.apply(lambda x: sp.spatial.distance.pdist(x.values.reshape(-1, 1), metric=lambda x, y: edit_distance(x[0], y[0], transpositions=True)), axis=1)
    pw_distances = pw_distances.apply(sp.spatial.distance.squareform)

    return pw_distances




def get_linkage_matrix(model):

    # create the counts of samples under each node
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1  # leaf node
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count

    linkage_matrix = np.column_stack(
        [model.children_, model.distances_, counts]
    ).astype(float)

    return linkage_matrix




def plot_dendrogram(Z, circular=False, **kwargs):
    
    if not circular:
        dendrogram(Z, **kwargs)

    else:
        #Get lines from dendrogram
        kwargs['no_plot'] = True
        R = dendrogram(Z, **kwargs)
        X, Y = np.array(R['icoord']), np.array(R['dcoord'])

        #Perform polar transform
        xmin, xmax = X.min(), X.max()
        ymin, ymax = Y.min(), Y.max()

        r = abs((Y - ymax)/(ymin - ymax))
        delta = 0.03 #Extra room near 0 degrees
        theta = 2*math.pi*(X - xmin + delta*(xmax/xmin))/(xmax - xmin + 2*delta*(xmax/xmin))

        #Plot lines
        if 'ax' in kwargs:
            ax = kwargs['ax']
        else:
            fig, ax = plt.subplots()

        for i in range(r.shape[0]):
            
            for j in range(3):
                r1, r2 = r[i, j], r[i, j+1]
                t1, t2 = theta[i, j], theta[i, j+1]

                N = 50
                ax.plot(np.linspace(t1, t2, N), np.linspace(r1, r2, N), color=R['color_list'][i], lw=1)

        #Annotate
        if 'labels' in kwargs:
            ax.set_rmax(1)
            ax.set_rticks([])
            ticks =  2*math.pi*(np.arange(5, 10*len(R['ivl'])+5, 10) - xmin + delta*(xmax/xmin))/(xmax - xmin + 2*delta*(xmax/xmin))
            ax.set_xticks(ticks)
            ticklabels = R['ivl']
            ax.set_xticklabels(ticklabels)

            plt.gcf().canvas.draw()
            angles = np.linspace(0,2*np.pi,len(ax.get_xticklabels())+1)
            angles[np.cos(angles) < 0] = angles[np.cos(angles) < 0] + np.pi
            angles = np.rad2deg(angles)
            labels = []

            leaves_color_list = [None] * len(R['leaves'])
            for link_x, link_y, link_color in zip(R['icoord'],
                                          R['dcoord'],
                                          R['color_list']):
                for (xi, yi) in zip(link_x, link_y):
                    if yi == 0.0:  # if yi is 0.0, the point is a leaf
                        # xi of leaves are      5, 15, 25, 35, ... (see `iv_ticks`)
                        # index of leaves are   0,  1,  2,  3, ... as below
                        if int(xi)%10!=0:
                            leaf_index = (int(xi) - 5) // 10
                            # each leaf has a same color of its link.
                            leaves_color_list[leaf_index] = link_color

            i=0
            for label, angle in zip(ax.get_xticklabels(), angles):
                x,y = label.get_position()
                lab = ax.text(x,y-0.2, label.get_text(), transform=label.get_transform(),
                            ha=label.get_ha(), va=label.get_va(), fontsize=6, color=leaves_color_list[i])
                i += 1
                lab.set_rotation(angle)
                labels.append(lab)
            ax.set_xticklabels([])
            plt.axis('off')

            #Add leaf markers
            ax.scatter(ticks, np.ones(ticks.size), marker='o', s=3, c=leaves_color_list)

        else:
            ax.set_xticks([])

    return