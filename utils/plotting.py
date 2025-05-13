# utils/plotting.py

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets

def setup_plot(num_channels):
    """Crée une fenêtre avec plusieurs courbes de tracé PyQtGraph."""
    win = pg.GraphicsLayoutWidget(title="Signaux multicanaux")
    plots = []
    curves = []

    for i in range(num_channels):
        p = win.addPlot(title=f"Canal {i}")
        p.showGrid(x=True, y=True)
        curve = p.plot(pen=pg.intColor(i))
        plots.append(p)
        curves.append(curve)
        win.nextRow()
    
    return win, plots, curves

def update_plot(curves, data):
    """Met à jour les courbes PyQtGraph avec de nouvelles données."""
    for i, curve in enumerate(curves):
        curve.setData(data[i])
