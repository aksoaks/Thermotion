

def check_devices_online(self):
        """Check if configured devices are online"""
        try:
            system = nidaqmx.system.System.local()
            online_devices = [d.name for d in system.devices]
            
            for module_name in self.module_widgets:
                device_name = next((k for k,v in self.config["devices"].items() 
                                if v["display_name"] == module_name), None)
                if device_name and device_name not in online_devices:
                    # Add offline indicator
                    for i in range(self.channel_list.count()):
                        item = self.channel_list.item(i)
                        widget = self.channel_list.itemWidget(item)
                        if widget and module_name in widget.text():
                            # Add offline label
                            offline_label = QLabel("(offline)")
                            offline_label.setStyleSheet("color: red;")
                            layout = widget.layout()
                            if layout:
                                layout.addWidget(offline_label)
        except Exception as e:
            print(f"Device check error: {str(e)}")

    
def scan_devices(self):
        """Open device scanner dialog"""
        dialog = DeviceScannerDialog(self)
        dialog.config_updated.connect(self.update_config)
        dialog.exec()    