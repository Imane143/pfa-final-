# create_directories.py
import os

# Chemin du script actuel
current_dir = os.path.dirname(os.path.abspath(__file__))

# Créer le répertoire pour les historiques de conversation
history_folder = os.path.join(current_dir, "conversation_histories")
if not os.path.exists(history_folder):
    os.makedirs(history_folder)
    print(f"Répertoire créé: {history_folder}")
else:
    print(f"Le répertoire existe déjà: {history_folder}")

print("Configuration terminée!")