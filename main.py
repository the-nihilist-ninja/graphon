# %%
# 
from pathlib import Path

import torch
from embedding import create_g2v_embeddings, load_embeddings, histogram_embeddings
from data_loader.syntheticData import SynthGraphons
from utils import classification, clustering, update_config, download_datasets, load_graph, combine_datasets
import numpy as np
import wandb
import yaml
import time
import os
import random 

def clustering_classification(
    NUM_GRAPHS_PER_GRAPHON=100,
    NUM_NODES=None,
    N0=30,
    SAVE_GRAPHONS=False,
    CREATE_EMBEDDINGS=False,
    G2V_EMBEDDING_DIR=None,
    DATA=None,
    SWEEP=False,
    DOWNLOAD_DATA=False,
    AUGMENT_DATA=False,
    SYNTH_DATA=True
    
):
    if SYNTH_DATA:
        assert NUM_NODES > N0, 'N0 must be smaller than NUM_NODES'
        NUM_GRAPHONS = len(DATA[1])
        k = NUM_GRAPHONS
        parent_dir = Path('graphons_dir')
        parent_dir.mkdir(exist_ok=True, parents=True)
        GRAPHONS_DIR = parent_dir.joinpath(f'{NUM_GRAPHONS}_graphons_{NUM_GRAPHS_PER_GRAPHON}_graphs.pkl')

        # synthetic data_loader
        if SAVE_GRAPHONS:
            syn_graphons = SynthGraphons(NUM_NODES, NUM_GRAPHS_PER_GRAPHON, DATA[1])
            graphs, true_labels = syn_graphons.data_simulation(start=100, stop=1000)
            syn_graphons.save_graphs(GRAPHONS_DIR)
        else:
            graphs, true_labels = SynthGraphons.load_graphs(path=GRAPHONS_DIR)
        if AUGMENT_DATA:
            print('Performing data augmentation')
            graphs, true_labels = augment_dataset(graphs, true_labels, extra_graphs=10)
    else:
        if DOWNLOAD_DATA:
            download_datasets()
        # loading graphs
        fb = load_graph(min_num_nodes=N0, name=DATA[0][0])
        github = load_graph(min_num_nodes=N0, name=DATA[0][2])
        reddit = load_graph(min_num_nodes=N0, name=DATA[0][3])
        deezer = load_graph(min_num_nodes=N0, name=DATA[0][1])
        # graphs, true_labels = combine_datasets([fb, github, reddit])
        # graphs, true_labels = combine_datasets([fb, github, deezer])
        # graphs, true_labels = combine_datasets([fb, reddit, deezer])
        # graphs, true_labels = combine_datasets([github, reddit, deezer])
        graphs, true_labels = combine_datasets([fb, github, reddit, deezer])

        k = len(np.unique(true_labels))
        if AUGMENT_DATA:
            print('Performing data augmentation')
            graphs, true_labels = augment_dataset(graphs, true_labels)

    # start recording time for embedding creation
    start_t_g2v = time.time()

    # creating graph2vec embeddings of the graphs from graphons and storing them
    if CREATE_EMBEDDINGS:
        print('\nCreating graph2vec embeddings')
        create_g2v_embeddings(graph_list=graphs, true_labels=true_labels, dir_name=G2V_EMBEDDING_DIR)
    time_g2v = time.time() - start_t_g2v
    print(f'Graph2vec embeddings created in {time_g2v} seconds')

    
    # classification of graph2vec embeddings
    embeddings, true_labels = load_embeddings(dir_name=G2V_EMBEDDING_DIR)
    embeddings = np.squeeze(embeddings)
    print('Number of labels: ', len(true_labels))
    
    print('\nPerforming classification on histogram approximation')
    classification_train_acc, classification_test_acc = classification(embeddings, true_labels, GRAPH2VEC=True)

    print('performing clustering on histogram approximation')
    clustering_rand_score, clustering_error = clustering(embeddings, true_labels, k=k, GRAPH2VEC=True)

    if SWEEP:
        wandb.log({
            'g2v_class_train_accuracy': classification_train_acc, 
                    'g2v_class_test_accuracy': classification_test_acc,
                    'g2v_clustering_rand_score': clustering_rand_score,
                    'g2v_clustering_error': clustering_error,
                    'time_g2v': time_g2v})


    start_t_graphons = time.time()
    # classification of graphon embeddings
    print('creating histogram approximation of graphs')
    hist_embeddings = histogram_embeddings(graphs, n0=N0) 
    embeddings = []
    for i in range(len(hist_embeddings)):
        flattened_emb = hist_embeddings[i].numpy().flatten()
        embeddings.append(flattened_emb)
    time_graphons = time.time() - start_t_graphons
    print(f'Graphon embeddings created in {time_graphons} seconds')

    print('\nPerforming classification on histogram approximation')
    classification_train_acc, classification_test_acc = classification(embeddings, true_labels)

    print('performing clustering on histogram approximation')
    clustering_rand_score, clustering_error = clustering(embeddings, true_labels, k=k, GRAPH2VEC=False)

    if SWEEP:
        wandb.log({
            'graphons_class_train_accuracy': classification_train_acc, 
                    'graphons_class_test_accuracy': classification_test_acc,
                    'graphons_clustering_rand_score': clustering_rand_score,
                    'graphons_clustering_error': clustering_error,
                    'time_graphons': time_graphons})


def graphon_mixup(graphs, num_sample=20, n0=30):
    """
    Takes all the graphs of a specific class and generates new graphs by mixing them up.

    :param graphons: list of graphs of a specific class
    :type graphons: list

    :param la: lambda parameter for the mixup weights
    :type la: float

    :param num_sample: number of samples to be generated
    :type num_sample: int

    :return: list of new graphs
    :rtype: list
    """
    # two_graphs = random.sample(graphs, 2)
    min_dim = min([g.shape[0] for g in graphs])
    hist_approxs = histogram_embeddings(graphs, n0=min_dim)

    new_graphon = sum(hist_approxs) / len(hist_approxs)

    new_graphs = []

    while len(new_graphs) < num_sample:
        sample_graph = (np.random.rand(*new_graphon.shape) < new_graphon.numpy()).astype(np.int32)
        sample_graph = np.triu(sample_graph)
        sample_graph = sample_graph + sample_graph.T - np.diag(np.diag(sample_graph))
        sample_graph = sample_graph[sample_graph.sum(axis=1) != 0]
        sample_graph = sample_graph[:, sample_graph.sum(axis=0) != 0]
        if sample_graph.shape[0] > n0:
            A = torch.from_numpy(sample_graph)
            new_graphs.append(A)
  
    return new_graphs

def augment_dataset(graphs, true_labels, extra_graphs=None, n0=30):
    """
    Augments the dataset by generating new graphs for each class.

    :param graphs: array of graphs
    :type graphs: ndarray

    :param true_labels: array of labels
    :type true_labels: ndarray

    :return: augmented graphs and labels
    :rtype: ndarray, ndarray
    """

    print(f'Initial number of graphs: {len(graphs)}')
    number_of_graphs = {f'{i}': len([x for x in true_labels if x == i]) for i in set(true_labels)}
    max_number_of_graphs = max(number_of_graphs.values())

    # select only graphs from a specific label
    new_graphs = []
    new_labels = []
    for label in number_of_graphs.keys():
        
        i_graphs = [graphs[i] for i in range(len(graphs)) if true_labels[i] == int(label)]

        num_sample = max_number_of_graphs - number_of_graphs[label]
        if num_sample != 0:
            sampled_graphs = graphon_mixup(i_graphs, num_sample=num_sample, n0=n0)
            new_graphs.extend(sampled_graphs)
            new_labels.extend([int(label)] * num_sample)

    if extra_graphs is not None:
        for label in number_of_graphs.keys():
            i_graphs = [graphs[i] for i in range(len(graphs)) if true_labels[i] == int(label)]
            num_sample = extra_graphs
            sampled_graphs = graphon_mixup(i_graphs, num_sample=num_sample, n0=n0)
            new_graphs.extend(sampled_graphs)
            new_labels.extend([int(label)] * num_sample)

    graphs = np.append(graphs, np.array(new_graphs))
    true_labels = np.append(true_labels, np.array(new_labels))
    print(f'Final number of graphs: {len(graphs)}')
    return graphs.tolist(), true_labels.tolist()


def sweep(config=None):
    with wandb.init(config=config):
            clustering_classification(**wandb.config)


if __name__ == '__main__':
    # loads the config file
    with open("config.yaml", 'r') as stream:
        config_def = yaml.load(stream, Loader=yaml.FullLoader)

    with open('sweep_config.yaml', 'r') as f:
            sweep_configuration = yaml.load(f, Loader=yaml.FullLoader)
    final_config = update_config(sweep_configuration, config_def)

    # if we are sweeping, we update the config with the default values and start the sweep
    # else we run the code using the config_def values
    if config_def['SWEEP']:
        wandb.login()
        sweep_id = wandb.sweep(sweep_configuration, project="graphon", entity='seb-graphon')
        wandb.agent(sweep_id, sweep)
    else:
        clustering_classification(**final_config)


# %%
