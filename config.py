import json
import os
from typing import Dict, Optional
from base64 import b64encode, b64decode

class ConfigManager:
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(__file__), 'last_session.json')
        self.default_config = {
            'source': {
                'host': 'localhost',
                'port': '3306',
                'username': 'root',
                'password': '',
                'last_database': ''
            },
            'destination': {
                'host': 'localhost',
                'port': '3306',
                'username': 'root',
                'password': '',
                'last_database': ''
            },
            'save_passwords': False
        }

    def _encode_password(self, password: str) -> str:
        """Simple encoding of password (not encryption, just to avoid plain text)"""
        if not password:
            return ''
        return b64encode(password.encode()).decode()

    def _decode_password(self, encoded: str) -> str:
        """Decode the encoded password"""
        if not encoded:
            return ''
        try:
            return b64decode(encoded.encode()).decode()
        except:
            return ''

    def load_config(self) -> Dict:
        """Load configuration from file or return default if file doesn't exist"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Decode passwords if they were saved
                    if config.get('save_passwords', False):
                        for section in ['source', 'destination']:
                            if config[section].get('password'):
                                config[section]['password'] = self._decode_password(config[section]['password'])
                    return config
        except Exception as e:
            print(f"Warning: Could not load configuration: {e}")
        return self.default_config.copy()

    def save_config(self, config: Dict, save_passwords: bool = None) -> None:
        """
        Save configuration to file
        
        Args:
            config (Dict): Configuration to save
            save_passwords (bool, optional): Whether to save passwords
        """
        try:
            # Create a deep copy of the config to modify
            save_config = {
                'source': config['source'].copy(),
                'destination': config['destination'].copy(),
                'save_passwords': save_passwords if save_passwords is not None else config.get('save_passwords', False)
            }
            
            # Handle passwords based on save_passwords setting
            if not save_config['save_passwords']:
                # Remove passwords if not saving them
                save_config['source']['password'] = ''
                save_config['destination']['password'] = ''
            else:
                # Encode passwords if saving them
                save_config['source']['password'] = self._encode_password(save_config['source']['password'])
                save_config['destination']['password'] = self._encode_password(save_config['destination']['password'])
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save configuration
            with open(self.config_file, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
