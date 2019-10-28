import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from modules.base import ParameterizedModule, load_with_spec

class PatchBase(ParameterizedModule):
    '''
    PatchBase - Abstract class for patches preparation in ParameterizedPointNet
    Current class deals with: - sampling, aka centroids determination
                              - grouping, aka local region set construction

    ...

    Attributes
    ----------

    Methods
    -------
    forward(xyz, centroids, features)
       Prepares patches from xyz-data and concats additional features                       
    '''
    @abstractmethod
    def forward(self, xyz: torch.Tensor(), centroids: torch.Tensor = None, features: torch.Tensor = None) -> torch.Tensor:
        '''
        input: xyz: (B, 3, N) coordinates of the features,
               features: (B, C, N) descriptors of the features (normals, etc)
                         None by default
        output: new_features: (B, C+3, npoint, nsample) tensor
        '''
        new_features = xyz
        return new_features

    
