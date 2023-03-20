import numpy as np
import matplotlib.pyplot as plt

fig, axs = plt.subplots(4,4)
i = 0
for x in range(4):
    for y in range(4):
        data = np.load('test_' + str(i) + '.npy')
        axs[x,y].imshow(data, cmap='YlOrBr')
        i += 1
plt.show()
