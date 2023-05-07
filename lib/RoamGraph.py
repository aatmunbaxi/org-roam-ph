#!/usr/bin/python3.10

import os , glob
import numpy as np
from orgparse import load as orgload

from gtda.homology import VietorisRipsPersistence
from gtda.homology import FlagserPersistence

from gtda.graphs import GraphGeodesicDistance

from gtda.plotting import plot_diagram
import plotly.io as pio


class RoamGraph():
    """
    Stores information of a (possibly filtered) roam directory.

    Attributes
    -----------
    dirname : str
        name of directory to search
    tags : str list
        list of tags to exclude
    """
    def __init__(self, dirname, tags = None , exclude = False ):
        super(RoamGraph, self).__init__()
        self.dirname = dirname
        self.tags= tags

        filenames = [os.path.join(dirname ,f) for f in glob.glob(dirname  + "*.org")]
        fileobs = [orgload(fname) for fname in filenames]
        roamIDs = [ f.get_property('ID') for f in fileobs ]

        self.nodedata = [(a,b,c) for (a,b,c) in zip(filenames, fileobs, roamIDs)]

        if tags:
            bool_tags_list = [self.contains_tag(i) for i in range(len(self.nodedata))]
            if exclude:
                bool_tags_list = [not i for i in bool_tags_list]
                # print(bool_tags_list)
            self.nodedata = [i for (i,v) in zip(self.nodedata, bool_tags_list) if v]



    def adjacency_matrix(self, directed = False):
        """
        Builds adjacency matrix of org-roam notes.

        directed -- whether to consider the zettel graph as directed (default False)
        """
        N = len(self.nodedata)

        graph = np.zeros((N,N))

        # Directed graph construction
        if directed:
            for i in range(N):
                for j in range(N):
                    if i != j:
                        graph[i,j] = self.__adjacency_entry(i,j,directed = True)
            return graph

        # Undirected graph construction
        for i in range(N):
            for j in range(i+1 , N):
                graph[i,j] = self.__adjacency_entry(i,j, directed = False)
                graph[j,i] = graph[i,j]

        return graph

    def distance_matrix(self, directed = False):
        """
        Computes distance matrix of graph

        directed -- Consider graph as directed (default False)
        """
        return GraphGeodesicDistance(directed=directed).fit_transform([self.adjacency_matrix(directed=directed)])

    def get_fnames(self):
        """
        Get filenames of graph
        """
        return [node[1] for node in self.nodedata]

    def get_nodedata(self):
        return self.nodedata

    def get_IDs(self):
        """
        Gets org-roam IDs of graph
        """
        return [node[2] for node in self.nodedata]

    def contains_tag(self,idx):
        """
        Determines if node at index idx contains any exclude tags
        """
        # node_body = ''
        # TODO Allow arbitrary depth specification here?
        # for subheading in self.nodedata[idx][1].root:
        #     node_body += subheading.get_body(format='raw')

        body = self.nodedata[idx][1].root.get_body(format='raw')
        return any(tag in body for tag in self.tags)

    def __adjacency_entry(self, i,j, directed = False):

        # print(i,j)
        for subheading in self.nodedata[i][1].root:
            if self.nodedata[j][2] in subheading.get_body(format='raw'):
                return 1

        # Check if there is a link point to ith node in jth node body
        if not directed:
            for subheading in self.nodedata[j][1].root:
                if self.nodedata[i][2] in subheading.get_body(format='raw'):
                    return 1

        return np.inf
