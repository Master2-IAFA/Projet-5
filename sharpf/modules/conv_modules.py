import torch
import torch.nn as nn
from sharpf.modules.base import ParameterizedModule


class ConvBase(ParameterizedModule):
    """
    ConvBase - Abstract class for Convolution methods for ParameterizedPointNet.
    Current class deals with point projection from one dimensionality to another.

    ...

    Attributes
    ----------

    Methods
    -------
    forward(x)
       Performs a convolution operation

    """
    def __init__(self, *args, **kwargs):
        super().__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        input: x: batch of points for interpolation, shape = (B, C_in, N_in, M_in)
                  B - batch size,
                  C_in - number of features
                  N_in - number of points
                  M_in - number of patches
        output: out: (B, C_out, N_out, M_out) tensor
        """
        return x


class StackedConv(ConvBase):
    """
    StackedConv - class for Convolution method for ParameterizedPointNet.
    Current class deals with point projection from one dimensionality to another.

    ...

    Attributes
    ----------
    channels: list, list of channels for convolutions; length of the list is blocks+1
    kernel_size: int, size of the window to perform convolution over
    bn: bool, whether to add BatchNormalization layer or not
    relu: bool, whether to add activation for the output or not
    blocks: int, number of convolution blocks to stack

    Methods
    -------
    forward(x)
       Performs a convolution operation

    """
    
    def __init__(
        self, 
        channels, 
        kernel_size=1, 
        bn=True, 
        relu=True, 
        dropout_prob=None,
        blocks=1, 
        **kwargs
    ):
        super().__init__(**kwargs)
        self.channels = channels
        self.kernel_size = kernel_size
        self.bn = bn
        self.relu = relu
        self.blocks = blocks
        self.dropout_prob = dropout_prob
        self.conv = conv_model_creator(
            channels=self.channels, 
            kernel_size=self.kernel_size, 
            blocks=self.blocks, 
            bn=self.bn, 
            relu=self.relu,
            dropout_prob=self.dropout_prob,

        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        input: x: batch of points for convolution, shape = (B, C_in, N_in, M_in)
                  B - batch size,
                  N_in - number of points
                  C_in - number of features
                  M_in - number of patches
        output: out: (B, N_out, C_out, M_out) tensor
        """
        out = self.conv(x.transpose(2, 1))
        return out.transpose(2, 1)


def conv_model_creator(channels=(6, 64), kernel_size=1, blocks=1, bn=True, relu=True, dropout_prob=None):
    layers = []
    assert blocks == len(channels)-1, 'wrong number of blocks'
        
    for i in range(blocks):
        layer = nn.Sequential(
            nn.Conv2d(channels[i], channels[i+1], kernel_size=kernel_size, bias=False),
            nn.BatchNorm2d(channels[i+1]) if bn else ConvBase(),
            nn.ReLU(inplace=True) if relu else ConvBase(),
        )
        layers.append(layer)
    if dropout_prob:
        layers.append(nn.Dropout(p=dropout_prob))
    
    return nn.Sequential(*layers)


conv_module_by_kind = {
    'conv_base': ConvBase,
    'stacked_conv': StackedConv
}