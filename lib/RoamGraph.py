#!/usr/bin/python
import os , glob , re
import warnings
import sqlite3 as sql

import numpy as np

from lib.RoamNode import RoamNode as Node

from scipy.sparse.csgraph import shortest_path

class RoamGraph():
    """
    Stores information of a (possibly filtered) roam directory.

    Attributes
    -----------
    dirname : str
        name of directory to search
    recurse : bool
        recurse into dirname
    ex_tags : str list
        list of tags to filter by. Regex supported
    include_ex : bool
        whether to exclude tags or include
    ex_tags : compiled python regex list
        list of regexes to filter tags by
    include_rx : bool
        include regex matched nodes
    nodes : list RoamNode
        list of RoamNodes
    """
    def __init__(self, db):
        """
        Constructor for RoamGraph

        Params
        db -- path to org-roam db (required)
        """

        super(RoamGraph, self).__init__()

        self.db_path = os.path.expanduser(db)

        id_list = self.__init_ids(self.db_path)

        fname_list = self.__init_fnames(self.db_path)

        titles_list = self.__init_titles(self.db_path)

        tags_list = self.__init_tags(self.db_path)

        links_to_list = self.__init_links_to(self.db_path)

        self.nodes = [ Node(a,b,c,d,e) for (a,b,c,d,e) in zip(fname_list, titles_list, id_list, tags_list, links_to_list) ]

    def get_nodes(self):
        """
        Returns list of nodes
        """
        return self.nodes

    def filter_tags(self, tags = None, exclude = True, regex = False):
        if not regex:
            self.__filter_tags(tags,exclude)

        if regex:
            self.__filter_rx_tags(tags,exclude)

    def __filter_tags(self,tags,exclude):
        scope = range(len(self.nodes))
        tfilter = [ node.has_tag(tags) for node in self.nodes ]
        if exclude:
            tfilter = [not val for val in tfilter]
        self.nodes = [ node for (node,val) in zip(self.nodes, tfilter) if val ]

    def __filter_rx_tags(self, tags, exclude):
        scope = range(len(self.nodes))
        tfilter  = [node.has_regex_tag(tags) for node in self.nodes]
        if exclude:
            tfilter = [not val for val in tfilter]
        self.nodes = [ node for (node,val) in zip(self.nodes, tfilter) if val ]

    def __init_ids(self,dbpath):
        """
        Initializes list of IDs for each node
        """
        id_query = 'SELECT id FROM nodes ORDER BY id ASC;'
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(id_query)
                return [i[0].replace('"','') for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ",e)

    def __init_fnames(self,dbpath):
        """
        Initializes list of filenames for each node
        """
        fname_query = 'SELECT file FROM nodes ORDER BY id ASC;'
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(fname_query)
                return [i[0].replace('"','') for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ",e)

    def __init_titles(self,dbpath):
        """
        Initializes list of titles for each node
        """
        title_query = 'SELECT title FROM nodes ORDER BY id ASC;'
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(title_query)
                return [i[0].replace('"','') for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ",e)

    def __init_tags(self,dbpath):
        """
        Initializes list of tags for each node
        """
        tags_query = 'SELECT GROUP_CONCAT(tag) FROM tags GROUP BY node_id ORDER BY node_id ASC;'
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(tags_query)
                clean = lambda s: s.replace('"', '')
                return [set(map(clean, i[0].split(','))) for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ",e)

    def __init_links_to(self,dbpath):
        """
        Initializes list of links
        """
        links_to_query = 'SELECT n.id, GROUP_CONCAT(l.dest) FROM nodes n LEFT JOIN links l ON n.id = l.source GROUP BY n.id ORDER BY n.id ;'
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(links_to_query)
                clean = lambda s: s.replace('"', '')
                links = query.fetchall()

                return [ set(map(clean,i[1].split(','))) if i[1] else {} for i in links ]

        except sql.Error as e:
            print("Connection failed: ",e)

    def remove_orphans(self):
        """
        Removes orphans from graph
        """
        mat = self.adjacency_matrix(directed=False)
        N = len(mat)

        mat += np.diag(np.full(N,np.inf))
        to_remove = []
        for i in range(N):
            if self.nodes[i].is_orphan([self.nodes[j] for j in range(N) if j != i]):
                to_remove.append(i)

        self.nodes = [self.nodes[i] for i in range(N) if i not in to_remove]

    def adjacency_matrix(self, directed = False, transpose = False):
        """
        Builds adjacency matrix of graph nodes

        directed -- whether to consider the zettel graph as directed (default False)
        transpose -- reverse direction of graph paths (default False)

        Returns graphs adjacency matrix
        """
        N = len(self.nodes)

        graph = np.zeros((N,N))

        if directed:
            for i in range(N):
                for j in range(N):
                    if i != j:
                        graph[i,j] = 1 if self.nodes[i].links(self.nodes[j]) else np.inf
            if transpose:
                return graph.transpose()

            return graph

        for i in range(N):
            for j in range(i+1,N):
                # print(type(self.nodes[i]) , type(self.nodes[j]))
                graph[i,j] = 1 if self.nodes[i].links(self.nodes[j]) else np.inf
                # if graph[i,j] == 1:
                #     print(f"{self.nodes[i]} links to {self.nodes[j]}" )

        graph += np.transpose(graph)

        return graph

    def distance_matrix(self, directed = False, transpose= False):
        """
        Computes distance matrix of graph

        directed -- Consider graph as directed (default False)
        transpose -- reverse direction of graph paths (default False)

        Returns graphs distance matrix
        """
        return shortest_path(self.adjacency_matrix(directed=directed) , directed=directed)

    def get_fnames(self,base = True):
        """
        Get filenames of graph

        base -- basenames of files (default True)
        """
        if base:
            return [os.path.basename(node.fname) for node in self.nodes]

        return [node.fname for node in self.nodes]

    def get_nodes(self):
        """
        Returns list of nodes
        """
        return self.nodes

    def get_IDs(self):
        """
        Returns list of node IDs
        """
        return [node.id for node in self.nodes]

    def get_titles(self):
        """
        Returns list of node names (#+title file property)
        """
        return [node.title for node in self.nodes]

    def links(self):
        links = [a.get_links() for a in self.nodes]
        return [(a,b) for (a,b) in zip(self.get_titles() ,links )]
