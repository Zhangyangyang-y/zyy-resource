from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.facecolor'] = '#f5f9ff'
        plt.rcParams['axes.facecolor'] = 'white'

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)

        # 统一配色
        self.colors = {
            'primary': '#4a8fe7',
            'secondary': '#7eb8f0',
            'accent': '#e74c3c',
            'grid': '#eef2f7',
            'text': '#2c3e50',
        }

    def style_axes(self):
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.spines['left'].set_color('#d0d8e3')
        self.axes.spines['bottom'].set_color('#d0d8e3')
        self.axes.tick_params(colors=self.colors['text'], labelsize=9)
        self.axes.grid(True, linestyle='--', alpha=0.4, color=self.colors['grid'])
