```markdown
# AutoFacture Asana

**AutoFacture Asana** est une application Python qui automatise la mise à jour des statuts de facturation dans Asana. L’application scanne une boîte mail (via IMAP) pour extraire les numéros de facture et le nom du client à partir des notifications de paiement, puis met à jour les tâches correspondantes dans Asana en utilisant l’API. L’interface graphique, réalisée avec Tkinter, facilite le déclenchement des opérations et le suivi via des logs détaillés.

---

## Fonctionnalités

- **Scan Automatique des E-mails**  
  Recherche dans le dossier spécifié (par ex. `INBOX/02-STRIPE`) les e-mails non lus dont l’objet commence par « Votre facture … a été payée en ligne ».

- **Extraction des Informations**  
  Utilisation d'expressions régulières pour extraire le numéro de facture (format `FXXXXXXXX-XXXX`) et le nom du client depuis le corps du mail.

- **Mise à jour dans Asana**  
  Recherche de la tâche dans un projet Asana grâce au numéro de facture et mise à jour du champ personnalisé « Paiement CG FRANCE » pour le passer à l’option « Payé ».

- **Interface Graphique**  
  Une interface conviviale permettant de lancer le scan des e-mails, d'afficher les résultats et de déclencher individuellement ou collectivement les mises à jour.

- **Gestion des Logs**  
  Enregistrement détaillé des actions (mises à jour réussies et erreurs) dans des fichiers de log.

---

## Installation

1. **Clonage du Dépôt**
   ```bash
   git clone https://github.com/tonutilisateur/AutoFactureAsana.git
   cd AutoFactureAsana
   ```

2. **Installation des dépendances**
   Assure-toi d’avoir Python 3.11+ installé, puis lance :
   ```bash
   pip install -r requirements.txt
   ```
   Les principales dépendances sont :
   - beautifulsoup4==4.12.2
   - requests==2.31.0
   - python-dotenv==1.0.1

3. **Configuration**
   Crée un fichier `.env` dans le répertoire racine avec le contenu suivant (en adaptant les valeurs) :
   ```
   IMAP_SERVER=imap.ionos.fr
   IMAP_PORT=993
   IMAP_USERNAME=ton.email@example.com
   IMAP_PASSWORD=ton_mot_de_passe
   ASANA_API_TOKEN=ton_token_asana
   ```

---

## Utilisation

Pour lancer l'application, exécute :

```bash
python AutoFactureAsana.py
```

- **Scan des e-mails :**  
  Clique sur le bouton « Scanner les e-mails » pour analyser la boîte mail et extraire les factures et clients.

- **Mise à jour Asana :**  
  Dans la fenêtre des résultats, chaque facture affichée dispose d’un bouton « Asana Payé » pour mettre à jour la tâche correspondante. Un bouton « Tout mettre à jour » permet de lancer la mise à jour pour toutes les factures extraites.

- **Logs :**  
  Les actions effectuées (réussites ou erreurs) sont enregistrées dans le dossier `log` situé dans le répertoire de l’application.

---

## Déploiement

Pour générer un exécutable Windows :

1. Utilise PyInstaller, par exemple :
   ```bash
   pyinstaller --onefile --windowed --add-data ".env;." --add-data "docs/documentation.html;docs" --add-data "docs/documentation_technique.html;docs" AutoFactureAsana.py
   ```
2. Le dossier de distribution final (par exemple, `dist/`) devrait contenir :
   - `AutoFactureAsana.exe`
   - `.env`
   - Le dossier `docs` (avec tes documentations)
   - Le dossier `log` sera créé automatiquement lors de la première exécution.

