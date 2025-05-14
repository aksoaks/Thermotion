import tkinter as tk
from tkinter import ttk

class ChannelConfigWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Channel Configuration")
        self.geometry("400x300")
        
        self.parent = parent
        
        # Configuration des voies
        self.channel_vars = []
        
        # Cadre principal
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Titre
        ttk.Label(main_frame, text="Configure Measurement Channels", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Cadre pour les cases à cocher des voies
        channel_frame = ttk.LabelFrame(main_frame, text="Active Channels")
        channel_frame.pack(fill='x', pady=5)
        
        # Création des cases à cocher pour chaque voie
        for i in range(8):  # Supposons 8 voies maximum
            var = tk.BooleanVar(value=(i == 0))  # Par défaut, AI0 est coché
            self.channel_vars.append(var)
            cb = ttk.Checkbutton(channel_frame, text=f"AI{i}", variable=var)
            cb.pack(anchor='w', padx=5, pady=2)
        
        # Boutons de validation
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Apply", command=self.apply_config).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='right', padx=5)
    
    def apply_config(self):
        """Applique la configuration sélectionnée"""
        selected_channels = []
        for i, var in enumerate(self.channel_vars):
            if var.get():
                selected_channels.append(f"AI{i}")
        
        print(f"Channels selected: {selected_channels}")  # Debug
        # Ici vous pourriez envoyer cette info au parent ou à votre système d'acquisition
        self.parent.update_channel_config(selected_channels)
        self.destroy()

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Thermotion - Measurement Interface")
        self.geometry("800x600")
        
        # Configuration par défaut
        self.active_channels = ["AI0"]
        
        self.create_widgets()
    
    def create_widgets(self):
        """Crée l'interface principale"""
        # Frame pour les boutons de contrôle
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Bouton Connect Device
        connect_btn = ttk.Button(control_frame, text="Connect Device", command=self.open_channel_config)
        connect_btn.pack(side='left', padx=5)
        
        # Bouton Start/Stop
        self.start_stop_btn = ttk.Button(control_frame, text="Start Measurement", state='disabled')
        self.start_stop_btn.pack(side='left', padx=5)
        
        # Zone d'affichage des graphiques
        graph_frame = ttk.Frame(self)
        graph_frame.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Label temporaire pour simulation
        self.graph_label = ttk.Label(graph_frame, text="Graph area - Selected channels: " + ", ".join(self.active_channels))
        self.graph_label.pack(expand=True)
    
    def open_channel_config(self):
        """Ouvre la fenêtre de configuration des voies"""
        ChannelConfigWindow(self)
    
    def update_channel_config(self, channels):
        """Met à jour la configuration des voies actives"""
        self.active_channels = channels
        self.graph_label.config(text="Graph area - Selected channels: " + ", ".join(self.active_channels))
        
        # Active le bouton Start si au moins une voie est sélectionnée
        if channels:
            self.start_stop_btn.config(state='normal')
        else:
            self.start_stop_btn.config(state='disabled')

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()