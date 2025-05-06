from features.app_shortcuts import AppShortcutFeature, AppShortcutConfigManager

# In the initialization section of the KeyboardConfigApp class, replace the existing app_shortcuts instantiation with:
        # Initialize app shortcut feature with dedicated config manager
        self.app_shortcut_config = AppShortcutConfigManager(self.shortcut_manager.config_dir)
        self.app_shortcuts = AppShortcutFeature(self.app_shortcut_config, self, self.shortcut_lighting) 