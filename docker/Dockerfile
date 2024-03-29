FROM nvidia/cuda:9.2-cudnn7-devel-ubuntu16.04

## Base packages for ubuntu

# clean the libs list
RUN apt-get clean \
 && apt-get update -qq \
 && apt-get install -y --no-install-recommends \
    git \
    wget \
    bzip2 \
    vim \
    nano \
    g++ \
    make \
    build-essential \
    software-properties-common \
    apt-transport-https \
    sudo \
    gosu \
    libgl1-mesa-glx \
    graphviz \
    tmux \
    screen \
    htop \
    p7zip-full \
    libeigen3-dev \
    libgmp-dev \
    libgmpxx4ldbl \
    libmpfr-dev \
    libboost-dev \
    libboost-thread-dev \
    libtbb-dev \
    parallel

RUN wget https://github.com/Kitware/CMake/releases/download/v3.17.4/cmake-3.17.4-Linux-x86_64.sh \
 && sh cmake-3.17.4-Linux-x86_64.sh --skip-license --prefix=/usr


# Create a non-root user and switch to it.
RUN adduser --disabled-password --gecos '' --shell /bin/bash user
RUN echo "user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-user
USER user

# All users can use /home/user as their home directory.
ENV HOME=/home/user
RUN chmod 777 /home/user

## Download and install miniconda
RUN wget https://repo.continuum.io/miniconda/Miniconda3-4.6.14-Linux-x86_64.sh -O ~/miniconda.sh \
 && chmod +x ~/miniconda.sh \
 && ~/miniconda.sh -b -p ~/miniconda \
 && rm ~/miniconda.sh \
 && echo "export PATH=/home/user/miniconda/bin:$PATH" >>/home/user/.profile
ENV PATH /home/user/miniconda/bin:$PATH
ENV CONDA_AUTO_UPDATE_CONDA=false

# Create a Python 3.6 environment.
RUN /home/user/miniconda/bin/conda install conda-build \
 && /home/user/miniconda/bin/conda create -y --name py36 python=3.6.5 \
 && /home/user/miniconda/bin/conda clean -ya
ENV CONDA_DEFAULT_ENV=py36
ENV CONDA_PREFIX=/home/user/miniconda/envs/$CONDA_DEFAULT_ENV
ENV PATH=$CONDA_PREFIX/bin:$PATH

RUN conda install pytorch==1.2.0 torchvision==0.4.0 cudatoolkit==9.2 -c pytorch

## Install general requirements for the sharp features
COPY docker/requirements.txt /opt/requirements.txt
RUN pip install --upgrade pip \
 && pip install --default-timeout=1000 -r /opt/requirements.txt

# Install PyTorch Geometric.
ENV PATH=/usr/local/cuda/bin:$PATH
ENV CPATH=/usr/local/cuda/include:$CPATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV DYLD_LIBRARY_PATH=/usr/local/cuda/lib:$DYLD_LIBRARY_PATH

# Install pytorch_geometric and friends
#RUN pip install --verbose --no-cache-dir torch-scatter
#RUN pip install --verbose --no-cache-dir torch-sparse
#RUN pip install --verbose --no-cache-dir torch-cluster
#RUN pip install --verbose --no-cache-dir torch-spline-conv
#RUN pip install torch-geometric

# Install geometry-related packages
RUN conda install -c conda-forge \
    igl=0.4.1 \
    point_cloud_utils=0.15.1 \
    libspatialindex=1.9.3 \
    pyembree=0.1.6

RUN mkdir /home/user/code
COPY --chown=user contrib/pythonaabb /home/user/code/pythonaabb
RUN cd /home/user/code/pythonaabb && pip install .
RUN git clone https://github.com/Toblerity/rtree.git /home/user/code/rtree \
 && cd /home/user/code/rtree && python setup.py install

RUN git clone https://github.com/PyMesh/PyMesh.git /home/user/code/pymesh \
 && cd /home/user/code/pymesh \
 && git submodule update --init \
 && export PYMESH_PATH=`pwd` \
 && pip install -r /home/user/code/pymesh/python/requirements.txt \
 && python setup.py build \
 && python setup.py install
