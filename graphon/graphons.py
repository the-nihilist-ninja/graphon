import torch
import numpy as np
from config import *

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
class graphons_graphs():
    
    def __init__(self, num_graphs, graphons_keys):#both graphons_keys and num_nodes 
                                                             #are lists
        self.num_graphs = num_graphs
        self.graphons_keys = [int(item) for item in graphons_keys] #0 to 9

        
        # graphons for simulated data
    def graphon_1(self, x):
        'w(u,v) = u * v'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = u * v
        return graphon


    def graphon_2(self, x):
        'w(u,v) = exp{-(u^0.7 + v^0.7))}'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = torch.exp(-(torch.pow(u, 0.7) + torch.pow(v, 0.7)))
        return graphon


    def graphon_3(self, x):
        'w(u,v) = (1/4) * [u^2 + v^2 + u^(1/2) + v^(1/2)]'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = 0.25 * (torch.pow(u, 2) + torch.pow(v, 2) + torch.pow(u, 0.5) + torch.pow(u, 0.5))
        return graphon


    def graphon_4(self, x):
        'w(u,v) = 0.5 * (u + v)'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = 0.5 * (u + v)
        return graphon


    def graphon_5(self, x):
        'w(u,v) = 1 / (1 + exp(-10 * (u^2 + v^2)))'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = 1 / (1 + torch.exp(-10 * (torch.pow(u, 2) + torch.pow(v, 2))))
        return graphon


    def graphon_6(self, x):
        'w(u,v) = |u - v|'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = torch.abs(u - v)
        return graphon


    def graphon_7(self, x):
        'w(u,v) = 1 / (1 + exp(-(max(u,v)^2 + min(u,v)^4)))'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = 1 / (1 + torch.exp(-(torch.pow(torch.max(u, v), 2) + torch.pow(torch.min(u, v), 4))))
        return graphon


    def graphon_8(self, x):
        'w(u,v) = exp(-max(u, v)^(3/4))'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = torch.exp(-torch.pow(torch.max(u, v), 0.75))
        return graphon


    def graphon_9(self, x):
        'w(u,v) = exp(-0.5 * (min(u, v) + u^0.5 + v^0.5))'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = torch.exp(-0.5 * (torch.min(u, v) + torch.pow(u, 0.5) + torch.pow(v, 0.5)))
        return graphon


    def graphon_10(self, x):
        'w(u,v) = log(1 + 0.5 * max(u, v))'
        p = torch.zeros((x.shape[0], x.shape[0]), dtype=torch.float64).to(device=device)
        u = p + x.reshape(1, -1)
        v = p + x.reshape(-1, 1)
        graphon = torch.log(1 + 0.5 * torch.max(u, v))
        return graphon
     

    def generate_graphs(self, graphon_key, n):
        graph_gen = []

        for nn in n:
            x = torch.distributions.uniform.Uniform(0, 1).sample([nn]).to(device=device)
            graph_prob = eval('self.graphon_' + str(graphon_key+1) + '(x)')

            graph = torch.distributions.binomial.Binomial(1, graph_prob).sample()
            graph = torch.triu(graph, diagonal=1)
            graph = graph + graph.t()
            graph_gen.append(graph)

        return graph_gen


    def data_simulation(self, start=100, stop=1000):
        graphs = []
        labels = []
        for graphon in self.graphons_keys:
            p = torch.randperm(stop)
            if NUM_NODES == None:
                n = p[p > start][:self.num_graphs]
            else:
                n = [NUM_NODES] * self.num_graphs
            #print('nodes ', n)
            g = self.generate_graphs(graphon, n)
            graphs = graphs + g

        for i in range(len(self.graphons_keys)):
            l = i * np.ones(self.num_graphs)
            labels = labels + l.tolist()
        #print('graphs generated', len(graphs))
        #print('true labels ', labels)
        return graphs, labels