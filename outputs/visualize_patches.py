import numpy as np
import os
import h5py
import matplotlib.pyplot as plt

path = "./"

hdf5_file = "abc_0000_0_1.hdf5"

f = h5py.File(os.path.join(path, hdf5_file), 'r')

print(list(f.keys()))

image = f['image']
distances = f['distances']

print(distances.shape)
print(image.shape)

#fig, axs = plt.subplots(4,4)
#for i in range(image.shape[0]):
#    axs[].imshow(img)
#    plt.show()
#
fig, axs = plt.subplots(4,4)
i = 0
for x in range(4):
    for y in range(4):
        axs[x,y].imshow(distances[i], cmap = "YlOrBr")
        i += 1
print("ah")
fig.tight_layout()
plt.show()
