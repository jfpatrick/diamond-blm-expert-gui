from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import numpy as np

x1 = np.linspace(0, 10, num=20, endpoint=True)
y1 = []

x2 = np.linspace(0, 10, num=7, endpoint=True)
y2 = [0,1,1,1,0,0,0]

f = interp1d(x2,y2,kind='previous')

y1 = f(x1)
print(y1)
print(y2)


# f = interp1d(x, y)
# f2 = interp1d(x, y, kind='cubic')
#
# xnew = np.linspace(0, 10, num=41, endpoint=True)
# plt.plot(x, y, 'o', xnew, f(xnew), '-', xnew, f2(xnew), '--')
# plt.legend(['data', 'linear', 'cubic'], loc='best')
# plt.show()