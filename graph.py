import re
import networkx as nx
import logging
from copy import deepcopy 

key_rm = ['name', '放送期間', '放送時間', '公開', '上映時間', '次作', '回数', '放送分']
value_rm = ['', '同上', '日本', '日本語', '英語', '公式サイト', 'ほか', 'ステレオ放送', '文字多重放送','歴代エンディングテーマを参照',
            'フジテレビ番組基本情報']
count_once = True

def pre_create_graph(points, data):
    res = {}
    for name, point in points.items():
        if name not in data:
            logging('name mismatch in points and data')
            continue
        res[name] = {
            'point': point,
            'data': data[name]
        }
    return res

def create_graph(input):
    G = nx.Graph()
    for name in input:
        point = input[name]['point']
        G.add_node(name, genre='content', point=point)
        attrs = set()
        for k, v in input[name]['data'].items():
            #add first genre to node attribute
            if k == 'ジャンル':
                if len(v)==0:
                    G.nodes[name]['genre'] = v
                else:
                    G.nodes[name]['genre'] = v[0]
            elif k not in key_rm:
                for attr in v:
                    if attr not in input.keys() and attr not in value_rm: #do nothing for contents itself
                        if G.nodes.get(attr) is None: #first time
                            G.add_node(attr, genre='attribute', point=point)
                        elif not (attr in attrs and count_once): # from second time
                            G.nodes[attr]['point'] += point
                        G.add_edge(name, attr, relation=k) 
                        attrs.add(attr)

    return G

#pre process to visualize. 
#todo: implement in frontend
def reduce_node(input_G, max_number_of_nodes):
    G = deepcopy(input_G)
    threshold = 1.0
    first = True
    node_rm = deepcopy(value_rm)
    while len(G.nodes)>max_number_of_nodes or first:
        print('Threshold: ', threshold)
        print(' node num before simplify:', len(G.nodes))
        node_rm.extend([node for node,degree in dict(G.degree()).items() if degree < 2 and G.nodes[node]['genre'] is 'attribute']) #remove node based on degree
        node_rm.extend([node for node in G.nodes if  G.nodes[node]['point'] < threshold and G.nodes[node]['genre'] is 'attribute'])
        G.remove_nodes_from(node_rm)
        print(' node num after simplify:', len(G.nodes))
        threshold += 0.1
        first = False
    return G

#mix the closed genres
def merge_genre(input_G):
    G = deepcopy(input_G)
    for name in G.nodes:
        if G.nodes[name]['genre'] != 'attribute':
            if re.search( '(.*バラエティ.*)|(.*お笑い.*)', G.nodes[name]['genre']):
                G.nodes[name]['genre'] = 'バラエティ'
            if re.search( '.*ドラマ.*', G.nodes[name]['genre']):
                G.nodes[name]['genre'] = 'ドラマ'
            if re.search( '.*SF.*', G.nodes[name]['genre']):
                G.nodes[name]['genre'] = 'SF'
    return G
