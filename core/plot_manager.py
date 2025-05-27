def update_display(self):
        """Update UI based on current config"""
        self.plot_widget.clear()
        self.channel_list.clear()
        self.graph_items = {}

        # Initialize module_widgets if not exists (safety check)
        if not hasattr(self, 'module_widgets'):
            self.module_widgets = {}
        else:
            self.module_widgets.clear()

        if not self.config.get("devices"):
            self.start_btn.setEnabled(False)
            return

        # Organize channels by module
        modules = {}
        for device_name, device_cfg in self.config["devices"].items():
            module_name = device_cfg.get("display_name", device_name)
            if module_name not in modules:
                modules[module_name] = {
                    "device_name": device_name,
                    "channels": []
                }

            # Add simulated channels (replace with real channels)
            for i in range(4):  # Example for 4 channels per device
                channel_id = f"{device_name}/ai{i}"
                color = "#{:06x}".format(hash(channel_id) % 0xffffff)

                modules[module_name]["channels"].append({
                    "id": channel_id,
                    "display_name": f"Ch{i}",
                    "color": color,
                    "visible": True
                })

        # Add modules to display
        for i, (module_name, module_data) in enumerate(modules.items()):
            # Add separator line between modules (except first one)
            if i > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color: #888; margin: 5px 0;")

                separator_item = QListWidgetItem()
                separator_item.setFlags(separator_item.flags() & ~Qt.ItemIsSelectable)
                separator_item.setSizeHint(QSize(0, 1))  # Thin separator line
                self.channel_list.addItem(separator_item)
                self.channel_list.setItemWidget(separator_item, separator)

            # Module header with visibility control
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(5, 5, 5, 5)

            # Module visibility checkbox
            module_cb = QCheckBox()
            module_cb.setChecked(True)
            module_cb.stateChanged.connect(
                lambda state, mn=module_name: self.toggle_module_visibility(mn, state)
            )
            header_layout.addWidget(module_cb)

            # Centered module name
            name_label = QLabel(module_name)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("""
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            """)
            header_layout.addWidget(name_label, 1)  # Stretchable

            header_item = QListWidgetItem()
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            header_item.setSizeHint(header_widget.sizeHint())
            self.channel_list.addItem(header_item)
            self.channel_list.setItemWidget(header_item, header_widget)

            # Store module reference
            self.module_widgets[module_name] = {
                'checkbox': module_cb,
                'channels': [ch['id'] for ch in module_data["channels"]]
            }

            # Add channels
            for channel in module_data["channels"]:
                # Create plot item
                curve = self.plot_widget.plot(
                    [0, 1, 2, 3, 4],  # X values (time)
                    [0, 1, 4, 9, 16], # Y values (simulated data)
                    name=channel["display_name"],
                    pen=pg.mkPen(color=channel["color"], width=2)
                )

                # Create channel list item
                item = QListWidgetItem()
                item.setData(Qt.UserRole, channel["id"])

                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(2, 2, 2, 2)

                # Visibility checkbox
                cb = QCheckBox()
                cb.setChecked(True)
                cb.stateChanged.connect(
                    lambda state, cid=channel["id"]: self.toggle_channel_visibility(cid, state)
                )
                layout.addWidget(cb)

                # Color indicator
                color_label = QLabel()
                color_label.setFixedSize(16, 16)
                color_label.setStyleSheet(f"""
                    background-color: {channel['color']};
                    border: 1px solid #000;
                    border-radius: 3px;
                """)
                layout.addWidget(color_label)

                # Channel name
                name_label = QLabel(channel["display_name"])
                name_label.setStyleSheet("font-size: 12px;")
                layout.addWidget(name_label)
                layout.addStretch()

                # Edit button
                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon.fromTheme("document-edit"))
                edit_btn = QPushButton("✏️")  # Unicode pencil character
                edit_btn.setStyleSheet("font-size: 14px; padding: 0px;")
                edit_btn.setFixedSize(24, 24)
                edit_btn.setFixedSize(24, 24)
                edit_btn.clicked.connect(
                    partial(self.edit_channel, channel["id"])
                )
                layout.addWidget(edit_btn)

                item.setSizeHint(widget.sizeHint())
                self.channel_list.addItem(item)
                self.channel_list.setItemWidget(item, widget)

                # Store references
                self.graph_items[channel["id"]] = {
                    "curve": curve,
                    "config": channel,
                    "checkbox": cb
                }

        self.start_btn.setEnabled(True)